"""
DictParser.py - Lightweight OpenFOAM dictionary parser.

Extracts structured key-value summaries from OpenFOAM case dictionaries
for use in the ReportBuilder expert-mode pages.
"""
from __future__ import annotations

from pathlib import Path


class DictParser:
    """
    Parse OpenFOAM dictionary files into nested Python dicts,
    then extract only the fields that matter for reporting.
    """

    # ── low-level parser ────────────────────────────────────────────

    @staticmethod
    def _strip_comments(text: str) -> str:
        """Remove // line comments and /* block comments */."""
        import re
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        text = re.sub(r"//[^\n]*", "", text)
        return text

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """
        Split cleaned text into tokens.

        Keeps parenthesised identifiers intact at any nesting depth,
        e.g. div(phi,U) or div((nuEff*dev2(T(grad(U))))).
        Stand-alone ( ) are emitted as separate tokens for list values.
        """
        tokens: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            # skip whitespace
            if ch.isspace():
                i += 1
                continue
            # structural single-char tokens (except parens, handled below)
            if ch in "{};":
                tokens.append(ch)
                i += 1
                continue
            # stand-alone paren (not attached to a word)
            if ch in "()" and (not tokens or not tokens[-1][-1:].isalnum()):
                tokens.append(ch)
                i += 1
                continue
            # paren attached to preceding word token → extend with balanced parens
            if ch == "(" and tokens and tokens[-1][-1:].isalnum():
                depth = 0
                start = i
                while i < n:
                    if text[i] == "(":
                        depth += 1
                    elif text[i] == ")":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                tokens[-1] += text[start:i]
                continue
            # plain word / number
            start = i
            while i < n and text[i] not in " \t\n\r{}();":
                i += 1
            tokens.append(text[start:i])
        return tokens

    @classmethod
    def parse_tokens(cls, tokens: list[str], start: int = 0) -> tuple[dict, int]:
        """
        Recursive descent: consume tokens into a nested dict.

        Returns (parsed_dict, next_index).
        """
        result: dict = {}
        i = start
        while i < len(tokens):
            tok = tokens[i]

            if tok == "}":
                return result, i + 1  # end of current block

            if tok in (";", "(", ")"):
                i += 1
                continue

            # ── peek ahead to decide what this token is ──
            key = tok
            i += 1
            if i >= len(tokens):
                break

            nxt = tokens[i]

            # key { ... }  →  sub-dict
            if nxt == "{":
                sub, i = cls.parse_tokens(tokens, i + 1)
                result[key] = sub
                continue

            # key value ;  →  scalar / list accumulation
            values: list[str] = []
            while i < len(tokens) and tokens[i] not in ("{", "}"):
                if tokens[i] == ";":
                    i += 1
                    break
                # handle inline list  ( a b c )
                if tokens[i] == "(":
                    i += 1
                    inner: list[str] = []
                    while i < len(tokens) and tokens[i] != ")":
                        inner.append(tokens[i])
                        i += 1
                    i += 1  # skip ')'
                    values.append("(" + " ".join(inner) + ")")
                    continue
                values.append(tokens[i])
                i += 1

            result[key] = " ".join(values) if values else ""

        return result, i

    @classmethod
    def parse_file(cls, filepath: Path) -> dict:
        """Parse a single OpenFOAM dictionary file into a nested dict."""
        if not filepath.exists():
            return {}
        raw = filepath.read_text(errors="ignore")
        clean = cls._strip_comments(raw)
        tokens = cls._tokenize(clean)
        parsed, _ = cls.parse_tokens(tokens)
        # drop the FoamFile header — it's just metadata
        parsed.pop("FoamFile", None)
        return parsed

    # ── high-level extraction ───────────────────────────────────────

    @classmethod
    def extract_summary(cls, case_dir: Path) -> list[dict]:
        """
        Return an ordered list of summary sections.

        Each section is::

            {"title": "Section Name",
             "rows":  [("key", "value"), ...]}

        Only the rows that actually exist in the case are included.
        """
        case_dir = Path(case_dir)
        sections: list[dict] = []

        # ── 1. Solver setup (controlDict) ──
        cd = cls.parse_file(case_dir / "system" / "controlDict")
        if cd:
            rows = []
            for k in ("application", "deltaT", "endTime", "startTime",
                       "startFrom", "stopAt", "writeInterval",
                       "writeControl", "purgeWrite", "writeFormat",
                       "writePrecision", "timePrecision"):
                if k in cd:
                    rows.append((k, cd[k]))
            # list function-object names only
            funcs = cd.get("functions", {})
            if isinstance(funcs, dict) and funcs:
                rows.append(("functionObjects", ", ".join(funcs.keys())))
            if rows:
                sections.append({"title": "Solver Setup (controlDict)", "rows": rows})

        # ── 2. Numerical schemes (fvSchemes) ──
        fv = cls.parse_file(case_dir / "system" / "fvSchemes")
        if fv:
            rows = []
            for block_name in ("ddtSchemes", "gradSchemes", "divSchemes",
                               "laplacianSchemes", "interpolationSchemes",
                               "snGradSchemes"):
                block = fv.get(block_name, {})
                if isinstance(block, dict):
                    for field, scheme in block.items():
                        label = f"{block_name} → {field}"
                        rows.append((label, scheme))
                elif isinstance(block, str) and block:
                    rows.append((block_name, block))
            if rows:
                sections.append({"title": "Numerical Schemes (fvSchemes)", "rows": rows})

        # ── 3. Solution control (fvSolution) ──
        sol = cls.parse_file(case_dir / "system" / "fvSolution")
        if sol:
            rows = []
            # solvers block
            solvers = sol.get("solvers", {})
            if isinstance(solvers, dict):
                for field, cfg in solvers.items():
                    if isinstance(cfg, dict):
                        solver_type = cfg.get("solver", "?")
                        tol = cfg.get("tolerance", "")
                        relTol = cfg.get("relTol", "")
                        rows.append((f"solver({field})", f"{solver_type}  tol={tol}  relTol={relTol}"))

            # SIMPLE / PIMPLE / PISO block
            for algo in ("SIMPLE", "PIMPLE", "PISO","potentialFlow"):
                blk = sol.get(algo, {})
                if isinstance(blk, dict) and blk:
                    for k, v in blk.items():
                        if isinstance(v, dict):
                            # nested residualControl etc.
                            for kk, vv in v.items():
                                rows.append((f"{algo}.{k}.{kk}", str(vv)))
                        else:
                            rows.append((f"{algo}.{k}", str(v)))

            # relaxationFactors
            relax = sol.get("relaxationFactors", {})
            if isinstance(relax, dict):
                # can be flat or contain sub-dicts "equations" / "fields"
                for sub_key in ("fields", "equations"):
                    sub = relax.get(sub_key, {})
                    if isinstance(sub, dict):
                        for fld, val in sub.items():
                            rows.append((f"relaxation.{sub_key}.{fld}", str(val)))
                # flat entries
                for k, v in relax.items():
                    if k not in ("fields", "equations") and not isinstance(v, dict):
                        rows.append((f"relaxation.{k}", str(v)))

            if rows:
                sections.append({"title": "Solution Control (fvSolution)", "rows": rows})

        # ── 4. Domain decomposition ──
        dec = cls.parse_file(case_dir / "system" / "decomposeParDict")
        if dec:
            rows = []
            for k in ("numberOfSubdomains", "method"):
                if k in dec:
                    rows.append((k, dec[k]))
            # coeffs sub-dict (scotch / hierarchical / simple)
            for coeff_key in (f"{dec.get('method', '')}Coeffs",
                              "hierarchicalCoeffs", "simpleCoeffs"):
                blk = dec.get(coeff_key, {})
                if isinstance(blk, dict):
                    for kk, vv in blk.items():
                        rows.append((f"{coeff_key}.{kk}", str(vv)))
            if rows:
                sections.append({"title": "Decomposition (decomposeParDict)", "rows": rows})

        # ── 5. Turbulence model ──
        mt = cls.parse_file(case_dir / "constant" / "momentumTransport")
        if mt:
            rows = []
            for k in ("simulationType", "model", "RAS", "LES"):
                v = mt.get(k, "")
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        rows.append((f"{k}.{kk}", str(vv)))
                elif v:
                    rows.append((k, v))
            if rows:
                sections.append({"title": "Turbulence Model (momentumTransport)", "rows": rows})

        # ── 6. Physical properties ──
        pp = cls.parse_file(case_dir / "constant" / "physicalProperties")
        if not pp:
            # some older cases use transportProperties
            pp = cls.parse_file(case_dir / "constant" / "transportProperties")
        if pp:
            rows = []
            for k in ("transportModel", "nu"):
                v = pp.get(k, "")
                if v:
                    rows.append((k, str(v)))
            if rows:
                sections.append({"title": "Physical Properties", "rows": rows})

        return sections