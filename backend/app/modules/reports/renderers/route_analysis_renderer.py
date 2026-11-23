"""
WS-ROUT-5: Route Analysis Dedicated Report Renderers (XLSX and PDF)
Strictly renders immutable RouteAnalysisReportCanonical objects.
Preserves 100% numerical and decision parity with the database snapshot.
"""

import io
from typing import Any, List, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas

from app.modules.reports.schemas.route_analysis_canonical import RouteAnalysisReportCanonical


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.setTitle("Fleet Control Tower — Route Analysis Report")
        self.setAuthor("Fleet Control Tower Platform")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#64748B"))
        self.drawString(36, 20, "Fleet Control Tower — Ready Mix Concrete (RMC) Route Analysis Decision Support")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 20, page_text)
        self.restoreState()


class RouteAnalysisXLSXRenderer:
    @staticmethod
    def render(report: RouteAnalysisReportCanonical) -> bytes:
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        # Style Definitions
        title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
        section_font = Font(name="Calibri", size=12, bold=True, color="1E3A8A")
        sub_font = Font(name="Calibri", size=11, bold=True, color="3B82F6")
        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        card_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        highlight_fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
        bold_font = Font(name="Calibri", size=10, bold=True)
        regular_font = Font(name="Calibri", size=10)
        disclaimer_font = Font(name="Calibri", size=9, italic=True, color="64748B")

        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        # SHEET 1: 01_Decision_Summary
        ws1 = wb.create_sheet(title="01_Decision_Summary")
        ws1.views.sheetView[0].showGridLines = True

        ws1["A1"] = "Fleet Control Tower — Route Analysis Decision Support Report"
        ws1["A1"].font = title_font

        ws1["A3"] = "1. EXECUTIVE DECISION & RECOMMENDATION"
        ws1["A3"].font = section_font

        rec_color = "10B981" if "RECOMMEND_ALT" in report.recommendation_status else ("3B82F6" if "CURRENT" in report.recommendation_status else "F59E0B")
        status_fill = PatternFill(start_color="F0FDF4" if "RECOMMEND_ALT" in report.recommendation_status else "EFF6FF", fill_type="solid")

        exec_rows = [
            ("Recommendation Status:", report.recommendation_status),
            ("Decision Case Category:", report.decision_case),
            ("Recommended Source Plant:", f"{report.recommended_plant_name or report.recommended_plant_code or 'N/A'} (ID: {report.recommended_plant_id or 'N/A'})"),
            ("Current Approved Source Plant:", f"{report.current_source_plant_name or report.current_source_plant_code or 'N/A'} (ID: {report.current_source_plant_id or 'N/A'})"),
            ("Destination Job Site:", f"{report.site_name or report.site_code or 'N/A'} (ID: {report.site_id or 'N/A'})"),
            ("Customer Name:", f"{report.customer_name or report.customer_code or 'N/A'} (ID: {report.customer_id or 'N/A'})"),
            ("Estimated Route Time Saved:", f"{report.minutes_saved:.1f} mins" if report.minutes_saved is not None else "N/A"),
            ("Is Traffic Delay Override?:", "YES" if report.is_traffic_override else "NO"),
            ("Operational Explanation:", report.decision_reason_summary),
        ]

        for r_idx, (lbl, val) in enumerate(exec_rows, start=4):
            ws1.cell(row=r_idx, column=1, value=lbl).font = bold_font
            cell_val = ws1.cell(row=r_idx, column=2, value=str(val))
            cell_val.font = regular_font
            if lbl == "Recommendation Status:":
                cell_val.font = Font(name="Calibri", size=11, bold=True, color=rec_color)

        # Section 2: Analysis Parameters & Freshness
        start_sec2 = 4 + len(exec_rows) + 1
        ws1.cell(row=start_sec2, column=1, value="2. ANALYSIS PARAMETERS & GOVERNANCE").font = section_font

        param_rows = [
            ("Analysis Execution ID:", report.metadata.execution_id),
            ("Original Analysis UUID:", report.analysis_id),
            ("Analysis Mode:", report.analysis_mode),
            ("Planned Departure Time:", report.planned_departure_time or "N/A (Real-time NOW evaluation)"),
            ("Engine Version:", report.engine_version),
            ("Policy Version:", report.policy_version),
            ("Analysis Timestamp (UTC):", report.created_at),
            ("Google Routes Traffic Freshness:", f"{report.google_data_freshness_seconds}s (Fresh)" if report.is_google_fresh else f"{report.google_data_freshness_seconds}s (Cached/Historical)"),
            ("Historical Data Window:", "90 Days Rolling"),
            ("ERP Batch Lineage:", report.erp_import_batch_id or "N/A"),
        ]

        for r_idx, (lbl, val) in enumerate(param_rows, start=start_sec2 + 1):
            ws1.cell(row=r_idx, column=1, value=lbl).font = bold_font
            ws1.cell(row=r_idx, column=2, value=str(val)).font = regular_font

        # Disclaimer
        disc_row = start_sec2 + len(param_rows) + 2
        ws1.cell(row=disc_row, column=1, value=f"Operational Note: {report.disclaimer}").font = disclaimer_font

        # SHEET 2: 02_Candidate_Comparison
        ws2 = wb.create_sheet(title="02_Candidate_Comparison")
        ws2.views.sheetView[0].showGridLines = True

        ws2["A1"] = "CANDIDATE PLANT COMPARISON MATRIX"
        ws2["A1"].font = title_font

        headers_c = [
            "Plant Code",
            "Plant Name",
            "Role",
            "Viable?",
            "Crow-Fly Dist (km)",
            "Google Dist (km)",
            "Duration in Traffic (mins)",
            "Static Duration (mins)",
            "Traffic Delay (mins)",
            "Historical T1 p50 (mins)",
            "Historical IQR (mins)",
            "Hist Samples",
            "Confidence Level",
            "Historical Status",
        ]

        for col_idx, h in enumerate(headers_c, start=1):
            cell = ws2.cell(row=3, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center" if col_idx > 2 else "left")

        for r_idx, cand in enumerate(report.comparisons, start=4):
            role = "RECOMMENDED" if cand.is_recommended else ("CURRENT APPROVED" if cand.is_current_source else "CANDIDATE")
            row_vals = [
                cand.plant_code,
                cand.plant_name,
                role,
                "YES" if cand.is_viable else "NO",
                cand.crow_fly_distance_km,
                cand.google_distance_km if cand.google_distance_km is not None else "N/A",
                cand.google_duration_in_traffic_mins if cand.google_duration_in_traffic_mins is not None else "N/A",
                cand.google_static_duration_mins if cand.google_static_duration_mins is not None else "N/A",
                cand.google_traffic_delay_mins if cand.google_traffic_delay_mins is not None else "N/A",
                cand.historical_t1_p50_mins if cand.historical_t1_p50_mins is not None else "N/A",
                cand.historical_t1_iqr_mins if cand.historical_t1_iqr_mins is not None else "N/A",
                cand.historical_sample_count,
                cand.historical_confidence,
                cand.historical_winner_status,
            ]
            for col_idx, val in enumerate(row_vals, start=1):
                cell = ws2.cell(row=r_idx, column=col_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                if cand.is_recommended:
                    cell.fill = highlight_fill

        # SHEET 3: 03_Evidence_Audit
        ws3 = wb.create_sheet(title="03_Evidence_Audit")
        ws3.views.sheetView[0].showGridLines = True

        ws3["A1"] = "DUAL-EVIDENCE AUDIT & LINEAGE"
        ws3["A1"].font = title_font

        ws3["A3"] = "A. GOOGLE ROUTES API EVIDENCE"
        ws3["A3"].font = sub_font

        g_evidence = report.google_evidence_payload or {}
        g_rows = [
            ("Provider:", g_evidence.get("provider", "Google Routes API v2")),
            ("Routing Preference:", g_evidence.get("routing_preference", "TRAFFIC_AWARE")),
            ("Live Traffic Queried At:", report.google_queried_at or "N/A"),
            ("Cache Freshness Age:", f"{report.google_data_freshness_seconds} seconds"),
            ("Is Stale Cache?:", "YES" if report.is_google_stale_cache else "NO"),
            ("Provider Failure Code:", report.failure_reason_code or "NONE (Success)"),
        ]
        for r_idx, (lbl, val) in enumerate(g_rows, start=4):
            ws3.cell(row=r_idx, column=1, value=lbl).font = bold_font
            ws3.cell(row=r_idx, column=2, value=str(val)).font = regular_font

        start_h = 4 + len(g_rows) + 1
        ws3.cell(row=start_h, column=1, value="B. ERP HISTORICAL T1 OPERATIONAL EVIDENCE").font = sub_font

        h_evidence = report.historical_evidence_payload or {}
        h_rows = [
            ("Source Dataset:", "Authoritative ERP/VTS Completed Trips"),
            ("Historical Eligibility Window:", "90 Days"),
            ("T1 Duration Ingestion Bounds:", "5.0m to 300.0m"),
            ("Distance Ingestion Bounds:", "0.5 km to 150.0 km"),
            ("Historical Sample Sufficient?:", "YES" if report.is_historical_sufficient else "NO"),
            ("Overall Case Classification:", report.decision_case),
        ]
        for r_idx, (lbl, val) in enumerate(h_rows, start=start_h + 1):
            ws3.cell(row=r_idx, column=1, value=lbl).font = bold_font
            ws3.cell(row=r_idx, column=2, value=str(val)).font = regular_font

        # Auto-adjust column widths across all sheets
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 65)

        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()


class RouteAnalysisPDFRenderer:
    @staticmethod
    def render(report: RouteAnalysisReportCanonical) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
            title="Fleet Control Tower — Route Analysis Report",
            author="Fleet Control Tower Platform"
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=HexColor("#1E3A8A"),
        )
        h2_style = ParagraphStyle(
            "Heading2",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=HexColor("#1E3A8A"),
            spaceBefore=10,
            spaceAfter=4,
        )
        h3_style = ParagraphStyle(
            "Heading3",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=HexColor("#3B82F6"),
            spaceBefore=6,
            spaceAfter=3,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=HexColor("#1E293B"),
        )
        bold_body_style = ParagraphStyle(
            "BoldBody",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=HexColor("#1E293B"),
        )
        header_cell_style = ParagraphStyle(
            "HeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=HexColor("#FFFFFF"),
            alignment=1,  # Center
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            textColor=HexColor("#64748B"),
        )

        story = []

        # Title & Subtitle
        story.append(Paragraph("Fleet Control Tower — Route Analysis Decision Support", title_style))
        story.append(Paragraph(f"Immutable Decision Snapshot: <b>{report.analysis_id}</b>", h3_style))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1.5, color=HexColor("#1E3A8A"), spaceAfter=10))

        # Section 1: Executive Recommendation Callout Card
        story.append(Paragraph("1. Executive Operational Recommendation", h2_style))

        rec_plant_str = f"<b>{report.recommended_plant_name or report.recommended_plant_code or 'N/A'}</b>"
        curr_plant_str = f"<b>{report.current_source_plant_name or report.current_source_plant_code or 'N/A'}</b>"
        time_saved_str = f"<b>{report.minutes_saved:.1f} mins</b>" if report.minutes_saved is not None else "N/A"

        rec_table_data = [
            [
                Paragraph("<b>Recommendation Status:</b>", body_style),
                Paragraph(f"<b>{report.recommendation_status}</b>", bold_body_style),
                Paragraph("<b>Decision Case:</b>", body_style),
                Paragraph(report.decision_case, body_style),
            ],
            [
                Paragraph("<b>Recommended Plant:</b>", body_style),
                Paragraph(rec_plant_str, body_style),
                Paragraph("<b>Current Approved Plant:</b>", body_style),
                Paragraph(curr_plant_str, body_style),
            ],
            [
                Paragraph("<b>Destination Site:</b>", body_style),
                Paragraph(f"{report.site_name or report.site_code or 'N/A'}", body_style),
                Paragraph("<b>Customer:</b>", body_style),
                Paragraph(f"{report.customer_name or report.customer_code or 'N/A'}", body_style),
            ],
            [
                Paragraph("<b>Route Time Saved:</b>", body_style),
                Paragraph(time_saved_str, body_style),
                Paragraph("<b>Traffic Delay Override:</b>", body_style),
                Paragraph("YES" if report.is_traffic_override else "NO", body_style),
            ],
            [
                Paragraph("<b>Analysis Mode:</b>", body_style),
                Paragraph(f"{report.analysis_mode} ({report.planned_departure_time or 'Real-time NOW'})", body_style),
                Paragraph("<b>Google Freshness:</b>", body_style),
                Paragraph(f"{report.google_data_freshness_seconds}s age ({'Fresh' if report.is_google_fresh else 'Cached'})", body_style),
            ],
        ]

        t_summary = Table(rec_table_data, colWidths=[120, 150, 120, 150])
        t_summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 6))

        # Operational Explanation Callout
        exp_table = Table([[
            Paragraph(f"<b>Operational Explanation:</b><br/>{report.decision_reason_summary}", body_style)
        ]], colWidths=[540])
        exp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EFF6FF")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#3B82F6")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(exp_table)
        story.append(Spacer(1, 10))

        # Section 2: Candidate Comparison Matrix Table
        story.append(Paragraph("2. Candidate Plant Evidence & Comparison Matrix", h2_style))
        matrix_headers = [
            "Plant Code / Name",
            "Role",
            "Google Dist / Time",
            "Traffic Delay",
            "Hist T1 p50 (IQR)",
            "Samples",
            "Confidence",
        ]
        m_table_data = [[Paragraph(h, header_cell_style) for h in matrix_headers]]

        for cand in report.comparisons:
            role_text = "<b>RECOMMENDED</b>" if cand.is_recommended else ("CURRENT" if cand.is_current_source else "CANDIDATE")
            g_dist_time = f"{cand.google_distance_km or 0:.1f} km<br/>{cand.google_duration_in_traffic_mins or 0:.1f}m" if cand.google_distance_km is not None else "N/A"
            traf_delay = f"+{cand.google_traffic_delay_mins:.1f}m" if cand.google_traffic_delay_mins is not None else "0.0m"
            hist_p50_iqr = f"{cand.historical_t1_p50_mins:.1f}m (IQR: {cand.historical_t1_iqr_mins or 0:.1f}m)" if cand.historical_t1_p50_mins is not None else "N/A"

            m_table_data.append([
                Paragraph(f"<b>{cand.plant_code}</b><br/>{cand.plant_name}", body_style),
                Paragraph(role_text, body_style),
                Paragraph(g_dist_time, body_style),
                Paragraph(traf_delay, body_style),
                Paragraph(hist_p50_iqr, body_style),
                Paragraph(str(cand.historical_sample_count), body_style),
                Paragraph(cand.historical_confidence, body_style),
            ])

        m_table = Table(m_table_data, colWidths=[120, 75, 85, 65, 95, 45, 55])
        m_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1E3A8A")),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(m_table)
        story.append(Spacer(1, 10))

        # Section 3: Audit Lineage & Governance
        story.append(Paragraph("3. Immutable Audit Lineage & System Governance", h2_style))
        audit_data = [
            [
                Paragraph("<b>Execution ID:</b>", body_style),
                Paragraph(report.metadata.execution_id, body_style),
                Paragraph("<b>Analysis UUID:</b>", body_style),
                Paragraph(report.analysis_id, body_style),
            ],
            [
                Paragraph("<b>Engine Version:</b>", body_style),
                Paragraph(report.engine_version, body_style),
                Paragraph("<b>Policy Version:</b>", body_style),
                Paragraph(report.policy_version, body_style),
            ],
            [
                Paragraph("<b>Timestamp (UTC):</b>", body_style),
                Paragraph(report.created_at, body_style),
                Paragraph("<b>ERP Import Batch ID:</b>", body_style),
                Paragraph(report.erp_import_batch_id or "N/A", body_style),
            ],
        ]
        t_audit = Table(audit_data, colWidths=[120, 150, 120, 150])
        t_audit.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_audit)
        story.append(Spacer(1, 10))

        # Disclaimer
        story.append(Paragraph(f"<b>Operational Disclaimer:</b> {report.disclaimer}", disclaimer_style))

        doc.build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()
