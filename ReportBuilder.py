"""
ReportBuilder.py - Collects post-processing images into a PDF report.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from DictParser import DictParser

# ── Styling constants ──
DARK_BG     = HexColor("#1a1a2e") # define colour of background and text elements as constants for easy tweaking
ACCENT      = HexColor("#e94560") # define accent colour for stripes and highlights
WHITE       = HexColor("#ffffff") # define white colour for text and accents
LIGHT_GREY  = HexColor("#cccccc") # define light grey colour for secondary text and backgrounds
MID_GREY    = HexColor("#888888") # define mid grey colour for captions and footers
TITLE_FONT  = "Helvetica-Bold" # Define font for titles and headers as a constant for easy tweaking
BODY_FONT   = "Helvetica" # Define font for body text and captions as a constant for easy tweaking


class ReportBuilder:
    """
    Builds a multi-page PDF report from a list of image paths.

    Parameters
    ----------
    title       : Report title (e.g. "CFD Post-Processing Report")
    case_name   : Simulation OpenFOAM case identifier
    out_path    : Where to save the PDF
    author      : Optional author name
    description : Optional short description shown on cover page
    """

    def __init__(
        self,
        title: str = "CFD Post-Processing Report", # default title for the report, can be overridden when creating an instance of ReportBuilder
        case_name: str = "", # default case name (empty string), can be overridden when creating an instance of ReportBuilder
        out_path: str | Path = "report.pdf", # default output path for the generated PDF report, can be overridden when creating an instance of ReportBuilder
        author: str = "", # default author name (empty string), can be overridden when creating an instance of ReportBuilder
        description: str = "", # default description (empty string), can be overridden when creating an instance of ReportBuilder
        case_dir: str | Path | None = None,     
        include_expert_mode: bool = True,
    ):
        self.title = title # set the report title from the provided argument or use the default value
        self.case_name = case_name # set the case name from the provided argument or use the default value
        self.out_path = Path(out_path) # convert the provided output path to a Path object for easier file handling
        self.author = author # set the author name from the provided argument or use the default value
        self.description = description # set the description from the provided argument or use the default value
        self.case_dir = Path(case_dir) if case_dir else None   
        self.include_expert_mode = include_expert_mode 
        self.sections: list[dict] = [] # initialize an empty list to hold the sections of the report, where each section is represented as a dictionary containing image path, caption, and section name

    def add_image(self, path: str | Path, caption: str = "", section: str = ""): # method to add a single image to the report, takes the image path, an optional caption, and an optional section name as arguments
        """Register an image to include in the report."""
        p = Path(path)
        if not p.is_file(): # check if the provided path is a valid file, if not, print a warning message and skip adding this image to the report
            print(f"[ReportBuilder] WARNING: image not found, skipping: {p}")
            return
        self.sections.append({ # add the image information to the sections list as a dictionary containing the image path, caption, and section name
            "path": p,
            "caption": caption,
            "section": section,
        })

    def add_images(self, paths: list[Path], section: str = ""): # method to add multiple images to the report at once, takes a list of image paths and an optional section name as arguments
        """Register multiple images, using filenames as captions."""
        for p in paths:
            self.add_image(p, caption=p.stem.replace("_", " ").title(), section=section)
    

    def build(self) -> Path: # method to generate the PDF report, returns the path to the generated PDF file
        """Generate the PDF and return the output path."""
        self.out_path.parent.mkdir(parents=True, exist_ok=True) # ensure that the directory for the output path exists, creating it if necessary
        pagesize = landscape(A4) # set the page size to A4 in landscape orientation for the PDF report
        pw, ph = pagesize # unpack the page width and height from the pagesize tuple for later use in drawing elements on the PDF pages
        c = canvas.Canvas(str(self.out_path), pagesize=pagesize) # create a new canvas object for drawing the PDF, using the specified output path and page size

        self._draw_cover(c, pw, ph) # draw the cover page of the report using the private method _draw_cover, passing the canvas and page dimensions as arguments
        c.showPage() # move to the next page after drawing the cover page

        current_section = None # initialize a variable to keep track of the current section while iterating through the images, used to determine when to insert section divider pages
        for item in self.sections:
            # Section divider page
            if item["section"] and item["section"] != current_section: # check if the current image belongs to a new section by comparing its section name with the current_section variable, if it does, draw a section divider page using the _draw_section_divider method and update the current_section variable to the new section name
                current_section = item["section"]
                self._draw_section_divider(c, pw, ph, current_section) # draw a section divider page with the new section name using the private method _draw_section_divider, passing the canvas, page dimensions, and section title as arguments
                c.showPage()

            self._draw_image_page(c, pw, ph, item)
            c.showPage()

        if self.include_expert_mode and self.case_dir:
            expert_sections = DictParser.extract_summary(self.case_dir)
            if expert_sections:
                self._draw_section_divider(c, pw, ph, "Expert Mode — Simulation Setup")
                c.showPage()
                self._draw_expert_pages(c, pw, ph, expert_sections)
        c.save()
        print(f"[ReportBuilder] PDF saved: {self.out_path}") # prints a message to the console indicating that the PDF has been saved, along with the path to the generated PDF file
        return self.out_path

    # Private drawing methods

    def _draw_cover(self, c, pw, ph): # private method to draw the cover page of the report, takes the canvas and page dimensions as arguments
        """Dark cover page with title, case name, date."""
        # Background
        c.setFillColor(DARK_BG)
        c.rect(0, 0, pw, ph, fill=True, stroke=False)

        # Accent stripe
        c.setFillColor(ACCENT)
        c.rect(0, ph * 0.45, pw, 4 * mm, fill=True, stroke=False)

        # Title
        c.setFillColor(WHITE)
        c.setFont(TITLE_FONT, 36)
        c.drawCentredString(pw / 2, ph * 0.62, self.title)

        # Case name
        if self.case_name:
            c.setFont(BODY_FONT, 18)
            c.setFillColor(LIGHT_GREY)
            c.drawCentredString(pw / 2, ph * 0.54, self.case_name)

        # Description
        if self.description:
            c.setFont(BODY_FONT, 13)
            c.setFillColor(MID_GREY)
            c.drawCentredString(pw / 2, ph * 0.35, self.description)

        # Footer: author + date
        c.setFont(BODY_FONT, 11)
        c.setFillColor(MID_GREY)
        footer_parts = []
        if self.author: # if an author name is provided, add it to the footer_parts list to be included in the footer of the cover page
            footer_parts.append(self.author)
        footer_parts.append(datetime.now().strftime("%Y-%m-%d  %H:%M")) # add the current date and time to the footer_parts list, formatted as "YYYY-MM-DD HH:MM"
        c.drawCentredString(pw / 2, 25 * mm, "  |  ".join(footer_parts)) # draw the footer on the cover page by joining the elements of the footer_parts list with a separator " | " and centering it at the bottom of the page using the drawCentredString method of the canvas

    def _draw_section_divider(self, c, pw, ph, section_title): # private method to draw a section divider page, takes the canvas, page dimensions, and section title as arguments
        """Section divider page."""
        c.setFillColor(DARK_BG)
        c.rect(0, 0, pw, ph, fill=True, stroke=False)

        c.setFillColor(ACCENT)
        c.rect(pw * 0.1, ph * 0.48, pw * 0.8, 3 * mm, fill=True, stroke=False) # draw an accent stripe across the page to visually separate sections, positioned at 48% of the page height and spanning 80% of the page width, with a thickness of 3mm

        c.setFillColor(WHITE)
        c.setFont(TITLE_FONT, 30)
        c.drawCentredString(pw / 2, ph * 0.55, section_title)

    def _draw_image_page(self, c, pw, ph, item): # private method to draw a single image page with a caption and footer, takes the canvas, page dimensions, and image item as arguments
        """Single image page with caption and footer."""
        margin = 20 * mm
        header_h = 15 * mm
        footer_h = 18 * mm

        # Light background
        c.setFillColor(HexColor("#f5f5f5"))
        c.rect(0, 0, pw, ph, fill=True, stroke=False)

        # Top bar
        c.setFillColor(DARK_BG)
        c.rect(0, ph - header_h, pw, header_h, fill=True, stroke=False)
        c.setFillColor(ACCENT)
        c.rect(0, ph - header_h, pw, 1.5 * mm, fill=True, stroke=False)

        # Caption in header
        caption = item.get("caption", "")
        if caption:
            c.setFillColor(WHITE)
            c.setFont(TITLE_FONT, 13)
            c.drawString(margin, ph - header_h + 4.5 * mm, caption)

        # Image area
        img_x = margin
        img_y = footer_h
        img_w = pw - 2 * margin
        img_h = ph - header_h - footer_h - 5 * mm

        try:
            img = ImageReader(str(item["path"]))
            iw, ih = img.getSize()
            aspect = iw / ih

            # Fit within box preserving aspect ratio
            if img_w / img_h > aspect:
                draw_h = img_h
                draw_w = img_h * aspect
            else:
                draw_w = img_w
                draw_h = img_w / aspect

            # Centre in box
            draw_x = img_x + (img_w - draw_w) / 2
            draw_y = img_y + (img_h - draw_h) / 2

            c.drawImage(
                img, draw_x, draw_y, draw_w, draw_h,
                preserveAspectRatio=True, anchor="c",
            )
        except Exception as e:
            c.setFillColor(ACCENT)
            c.setFont(BODY_FONT, 12)
            c.drawCentredString(pw / 2, ph / 2, f"Could not load image: {e}")

        # Footer
        c.setFillColor(MID_GREY)
        c.setFont(BODY_FONT, 8)
        c.drawString(margin, 8 * mm, str(item["path"].name))
        c.drawRightString(pw - margin, 8 * mm, self.case_name)
    # Additional private methods for expert mode pages
    def _draw_expert_pages(self, c, pw, ph, expert_sections: list[dict]):
        """
        Render parsed dictionary data as clean key/value tables.

        Each section from DictParser.extract_summary() gets a titled
        block.  Rows are split across pages automatically.
        """
        margin = 20 * mm
        header_h = 14 * mm
        col_key_x = margin + 2 * mm          # left column (keys)
        col_val_x = pw * 0.42                 # right column (values)
        row_h = 5.5 * mm                      # row height
        section_gap = 8 * mm                  # gap between sections
        bottom_limit = 16 * mm                # stop drawing above this

        # ── start first page ──
        y = self._start_expert_page(c, pw, ph, header_h, margin)

        for sec in expert_sections:
            title = sec["title"]
            rows = sec["rows"]

            # check if section title + at least 2 rows fit
            needed = section_gap + 7 * mm + 2 * row_h
            if y - needed < bottom_limit:
                c.showPage()
                y = self._start_expert_page(c, pw, ph, header_h, margin)

            # ── section title ──
            y -= section_gap
            c.setFillColor(ACCENT)
            c.rect(margin, y - 1 * mm, pw - 2 * margin, 0.6 * mm,
                   fill=True, stroke=False)
            y -= 5.5 * mm
            c.setFillColor(DARK_BG)
            c.setFont(TITLE_FONT, 11)
            c.drawString(col_key_x, y, title)
            y -= 5 * mm

            # ── column headers ──
            c.setFillColor(MID_GREY)
            c.setFont(TITLE_FONT, 8)
            c.drawString(col_key_x, y, "Parameter")
            c.drawString(col_val_x, y, "Value")
            y -= 1 * mm
            c.setStrokeColor(LIGHT_GREY)
            c.setLineWidth(0.4)
            c.line(margin, y, pw - margin, y)
            y -= 4 * mm

            # ── data rows ──
            alt = False  # alternating row shading
            for key, val in rows:
                if y - row_h < bottom_limit:
                    c.showPage()
                    y = self._start_expert_page(c, pw, ph, header_h, margin)
                    y -= 4 * mm
                    alt = False

                # alternating background stripe
                if alt:
                    c.setFillColor(HexColor("#ebebeb"))
                    c.rect(margin, y - 1.2 * mm, pw - 2 * margin,
                           row_h, fill=True, stroke=False)
                alt = not alt

                # truncate long values to prevent overflow
                max_val_chars = 80
                display_val = val if len(val) <= max_val_chars else val[:max_val_chars] + " …"

                c.setFillColor(HexColor("#222222"))
                c.setFont("Courier", 8)
                c.drawString(col_key_x, y, key[:55])
                c.setFont(BODY_FONT, 8)
                c.drawString(col_val_x, y, display_val)

                y -= row_h

        # footer on last page
        self._expert_footer(c, pw, margin)
        c.showPage()

    def _start_expert_page(self, c, pw, ph, header_h, margin) -> float:
        """Draw expert-page background + header bar, return starting y."""
        c.setFillColor(HexColor("#f5f5f5"))
        c.rect(0, 0, pw, ph, fill=True, stroke=False)

        c.setFillColor(DARK_BG)
        c.rect(0, ph - header_h, pw, header_h, fill=True, stroke=False)
        c.setFillColor(ACCENT)
        c.rect(0, ph - header_h, pw, 1.5 * mm, fill=True, stroke=False)

        c.setFillColor(WHITE)
        c.setFont(TITLE_FONT, 12)
        c.drawString(margin, ph - header_h + 4 * mm, "Expert Mode — Simulation Setup")

        self._expert_footer(c, pw, margin)
        return ph - header_h - 8 * mm

    def _expert_footer(self, c, pw, margin):
        """Small footer with case name and date."""
        c.setFillColor(MID_GREY)
        c.setFont(BODY_FONT, 7)
        c.drawString(margin, 6 * mm, self.case_name)
        c.drawRightString(pw - margin, 6 * mm,
                          datetime.now().strftime("%Y-%m-%d %H:%M"))