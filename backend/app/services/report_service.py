
from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


NAVY = colors.HexColor("#10213A")
BLUE = colors.HexColor("#1677B8")
LIGHT = colors.HexColor("#EDF4FA")
GRAY = colors.HexColor("#64748B")

RISK_COLORS = {
    "LOW": colors.HexColor("#16A34A"),
    "MEDIUM": colors.HexColor("#D97706"),
    "HIGH": colors.HexColor("#EA580C"),
    "CRITICAL": colors.HexColor("#DC2626"),
}


def safe_text(value):
    return escape(str(value if value is not None else "N/A"))


def build_impact_report(
    prediction,
    ripple,
    risk,
    event_text=None,
    analysis=None,
):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=(595.28, 841.89),
        rightMargin=45,
        leftMargin=45,
        topMargin=48,
        bottomMargin=48,
        title="AtmoGraph Disruption Impact Report",
        author="AtmoGraph",
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitleCustom",
            parent=styles["Title"],
            fontSize=22,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportHeadingCustom",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=BLUE,
            spaceBefore=16,
            spaceAfter=9,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportBodyCustom",
            parent=styles["BodyText"],
            fontSize=9,
            leading=14,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSmallCustom",
            parent=styles["BodyText"],
            fontSize=8,
            leading=12,
            textColor=GRAY,
        )
    )

    story = []

    def paragraph(text, style="ReportBodyCustom"):
        return Paragraph(text, styles[style])

    def heading(text):
        story.append(paragraph(text, "ReportHeadingCustom"))

    def add_table(rows, widths=None):
        converted = [
            [paragraph(safe_text(cell)) for cell in row]
            for row in rows
        ]

        table = Table(
            converted,
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, LIGHT]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, BLUE),
                ]
            )
        )

        # Explicitly style the header paragraphs white.
        header_style = ParagraphStyle(
            "HeaderCellCustom",
            parent=styles["ReportBodyCustom"],
            textColor=colors.white,
            fontSize=8,
            leading=11,
        )

        for index, cell in enumerate(rows[0]):
            table._cellvalues[0][index] = Paragraph(
                safe_text(cell), header_style
            )

        story.append(table)

    story.append(
        paragraph("AtmoGraph", "ReportTitleCustom")
    )

    story.append(
        paragraph(
            "SUPPLY CHAIN DISRUPTION IMPACT REPORT",
            "ReportSmallCustom",
        )
    )

    story.append(Spacer(1, 12))

    generated = datetime.now(timezone.utc).strftime(
        "%d %B %Y, %H:%M UTC"
    )

    story.append(
        paragraph(f"<b>Generated:</b> {generated}")
    )

    story.append(
        paragraph(
            "<b>Disrupted entity:</b> "
            + safe_text(
                ripple.get("disrupted_name")
                or prediction.get("disrupted_entity")
            )
        )
    )

    if event_text:
        heading("1. Incident Description")
        story.append(paragraph(safe_text(event_text)))

    if analysis:
        story.append(
            paragraph(
                "<b>Detected disruption type:</b> "
                + safe_text(
                    analysis.get("disruption_type", "OTHER")
                )
            )
        )

    heading("2. Risk Assessment")

    risk_level = risk.get("risk_level", "UNKNOWN")
    risk_score = risk.get("risk_score", 0)

    story.append(
        paragraph(
            f"<b>Risk score:</b> {safe_text(risk_score)}/100"
        )
    )

    story.append(
        paragraph(
            "<b>Risk level:</b> " + safe_text(risk_level)
        )
    )

    story.append(
        paragraph(
            "<b>Event severity:</b> "
            + safe_text(risk.get("event_severity"))
        )
    )

    components = risk.get("score_components", {})

    add_table(
        [
            ["Risk Component", "Value"],
            [
                "Prediction exposure",
                f"{components.get('prediction_exposure', 0)}%",
            ],
            [
                "Graph reachability",
                f"{components.get('graph_reachability', 0)}%",
            ],
            [
                "Event severity weight",
                f"{components.get('event_severity_weight', 0)}%",
            ],
        ],
        [320, 185],
    )

    heading("3. GraphSAGE Prediction Summary")

    summary = prediction.get("summary", {})

    add_table(
        [
            ["Status", "Entity Count"],
            ["Normal", summary.get("normal", 0)],
            ["Affected", summary.get("affected", 0)],
            ["Disrupted", summary.get("disrupted", 0)],
        ],
        [320, 185],
    )

    heading("4. Downstream Ripple Analysis")

    story.append(
        paragraph(
            "<b>Reachable downstream entities:</b> "
            + safe_text(ripple.get("reachable_downstream", 0))
        )
    )

    story.append(
        paragraph(
            "<b>Maximum path length:</b> "
            + safe_text(ripple.get("max_hops", 0))
            + " hops"
        )
    )

    paths = ripple.get("affected_paths", [])

    if paths:
        rows = [["Downstream Entity", "Hops", "Shortest Path"]]

        for item in paths:
            rows.append(
                [
                    item.get("node_name", item.get("node_id")),
                    item.get("hops", 0),
                    " -> ".join(item.get("path_names", [])),
                ]
            )

        add_table(rows, [145, 55, 305])

    heading("5. Suggested Mitigation Actions")

    recommendations = []

    if ripple.get("reachable_downstream", 0) > 0:
        recommendations.append(
            "Review alternate transport routes and "
            "distribution options."
        )

    if summary.get("affected", 0) > 0:
        recommendations.append(
            "Prioritize monitoring of potentially "
            "affected warehouses and retailers."
        )

    if risk_level in ("HIGH", "CRITICAL"):
        recommendations.append(
            "Escalate the incident and evaluate "
            "contingency inventory."
        )

    if not recommendations:
        recommendations.append(
            "Continue monitoring the network."
        )

    for index, recommendation in enumerate(
        recommendations, start=1
    ):
        story.append(
            paragraph(
                f"{index}. {safe_text(recommendation)}"
            )
        )

    heading("6. Methodology and Limitations")

    story.append(
        paragraph(
            "GraphSAGE predictions are generated using "
            "a synthetic supply-chain network. Ripple "
            "paths represent directed graph reachability. "
            "The risk score is a weighted heuristic, "
            "not a calibrated probability of financial "
            "loss or operational disruption."
        )
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(
            45, 28,
            "AtmoGraph | Experimental Supply Chain Analysis"
        )
        canvas.drawRightString(
            550, 28,
            f"Page {doc.page}"
        )
        canvas.restoreState()

    document.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )

    buffer.seek(0)
    return buffer.getvalue()
