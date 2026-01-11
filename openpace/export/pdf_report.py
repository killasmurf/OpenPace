"""
PDF Report Generator

Generates comprehensive PDF clinical reports with:
- Patient demographics
- Device information
- Battery status and predictions
- Lead impedance trends
- Arrhythmia burden analysis
- Charts and visualizations
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from openpace.database.models import Patient, Transmission, LongitudinalTrend
from openpace.analysis.battery_analyzer import BatteryAnalyzer
from openpace.analysis.impedance_analyzer import ImpedanceAnalyzer
from openpace.analysis.arrhythmia_analyzer import ArrhythmiaAnalyzer


class PDFReportGenerator:
    """
    Generates PDF clinical reports for pacemaker data.

    Creates comprehensive reports with patient information, device status,
    trends, and clinical recommendations.
    """

    def __init__(self, page_size=letter):
        """
        Initialize PDF report generator.

        Args:
            page_size: Page size (letter or A4)
        """
        self.page_size = page_size
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f4788'),
            spaceBefore=12,
            spaceAfter=6,
            borderWidth=1,
            borderColor=colors.HexColor('#1f4788'),
            borderPadding=5
        ))

        # Recommendation style
        self.styles.add(ParagraphStyle(
            name='Recommendation',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#d32f2f'),
            leftIndent=20,
            spaceBefore=6,
            spaceAfter=6,
            borderWidth=1,
            borderColor=colors.HexColor('#d32f2f'),
            borderPadding=8,
            backColor=colors.HexColor('#ffebee')
        ))

    def generate_report(self,
                       patient: Patient,
                       transmissions: List[Transmission],
                       trends: Dict[str, LongitudinalTrend],
                       output_path: str,
                       anonymize: bool = False) -> str:
        """
        Generate comprehensive PDF report.

        Args:
            patient: Patient object
            transmissions: List of transmissions
            trends: Dictionary of trend data
            output_path: Output file path
            anonymize: Whether to anonymize patient data

        Returns:
            Path to generated PDF file
        """
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.page_size,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Build story (content)
        story = []

        # Title page
        story.extend(self._create_title_page(patient, anonymize))
        story.append(PageBreak())

        # Executive summary
        story.extend(self._create_executive_summary(patient, transmissions, trends, anonymize))
        story.append(Spacer(1, 0.2*inch))

        # Battery analysis
        if 'battery_voltage' in trends:
            story.extend(self._create_battery_section(trends['battery_voltage']))
            story.append(Spacer(1, 0.2*inch))

        # Lead analysis
        lead_trends = {k: v for k, v in trends.items() if k.startswith('lead_impedance')}
        if lead_trends:
            story.extend(self._create_lead_section(lead_trends))
            story.append(Spacer(1, 0.2*inch))

        # Arrhythmia analysis
        if 'afib_burden_percent' in trends:
            story.extend(self._create_arrhythmia_section(trends['afib_burden_percent']))

        # Build PDF
        doc.build(story)

        return output_path

    def _create_title_page(self, patient: Patient, anonymize: bool) -> List:
        """Create title page."""
        elements = []

        # Title
        title = Paragraph("OpenPace Device Report", self.styles['CustomTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))

        # Patient info table
        if anonymize:
            patient_name = "ANONYMIZED"
            patient_id = "XXX-XXX-XXXX"
            dob = "XXXX-XX-XX"
        else:
            patient_name = patient.patient_name
            patient_id = patient.patient_id
            dob = patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else "Unknown"

        data = [
            ['Patient Name:', patient_name],
            ['Patient ID:', patient_id],
            ['Date of Birth:', dob],
            ['Gender:', patient.gender or 'Unknown'],
            ['Report Generated:', datetime.now().strftime('%Y-%m-%d %H:%M')]
        ]

        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.5*inch))

        # Disclaimer
        disclaimer = Paragraph(
            "<b>DISCLAIMER:</b> This report is generated for educational and "
            "informational purposes only. It is not intended for clinical "
            "decision-making or patient care without appropriate validation "
            "and regulatory approval.",
            self.styles['Normal']
        )
        elements.append(disclaimer)

        return elements

    def _create_executive_summary(self, patient: Patient, transmissions: List[Transmission],
                                  trends: Dict[str, LongitudinalTrend], anonymize: bool) -> List:
        """Create executive summary section."""
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))

        # Transmission count and date range
        if transmissions:
            first_trans = min(transmissions, key=lambda t: t.transmission_date)
            last_trans = max(transmissions, key=lambda t: t.transmission_date)

            summary_data = [
                ['Total Transmissions:', str(len(transmissions))],
                ['First Transmission:', first_trans.transmission_date.strftime('%Y-%m-%d')],
                ['Last Transmission:', last_trans.transmission_date.strftime('%Y-%m-%d')],
                ['Device Manufacturer:', last_trans.device_manufacturer or 'Unknown'],
                ['Device Model:', last_trans.device_model or 'Unknown']
            ]

            table = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey)
            ]))

            elements.append(table)

        return elements

    def _create_battery_section(self, trend: LongitudinalTrend) -> List:
        """Create battery analysis section."""
        elements = []

        elements.append(Paragraph("Battery Status", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))

        try:
            analysis = BatteryAnalyzer.analyze_depletion(trend)

            if 'error' not in analysis:
                # Battery metrics table
                data = [
                    ['Current Voltage:', f"{analysis['current_voltage']:.2f} V"],
                    ['Depletion Rate:', f"{abs(analysis['depletion_rate_v_per_year']):.3f} V/year"],
                    ['Remaining Capacity:', f"{analysis['remaining_capacity_percent']:.1f}%"],
                    ['Years to ERI:', f"{analysis['years_to_eri']:.1f} years" if analysis['years_to_eri'] else "N/A"],
                    ['Predicted ERI Date:', analysis['predicted_eri_date'] or "N/A"],
                    ['Confidence:', analysis['confidence'].title()]
                ]

                table = Table(data, colWidths=[2.5*inch, 3.5*inch])
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6)
                ]))

                elements.append(table)
                elements.append(Spacer(1, 0.1*inch))

                # Recommendation
                recommendation = BatteryAnalyzer.get_recommendation(analysis)
                rec_para = Paragraph(f"<b>Recommendation:</b> {recommendation}", self.styles['Recommendation'])
                elements.append(rec_para)

        except Exception as e:
            elements.append(Paragraph(f"Error analyzing battery: {str(e)}", self.styles['Normal']))

        return elements

    def _create_lead_section(self, lead_trends: Dict[str, LongitudinalTrend]) -> List:
        """Create lead impedance analysis section."""
        elements = []

        elements.append(Paragraph("Lead Impedance Status", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))

        for lead_name, trend in lead_trends.items():
            try:
                analysis = ImpedanceAnalyzer.analyze_trend(trend)

                # Lead info
                lead_title = analysis['lead_name']
                elements.append(Paragraph(f"<b>{lead_title} Lead</b>", self.styles['Heading3']))

                data = [
                    ['Current Impedance:', f"{analysis['current_impedance']:.0f} Ohms"],
                    ['Mean Impedance:', f"{analysis['mean_impedance']:.0f} Ohms"],
                    ['Stability Score:', f"{analysis['stability']['score']:.0f}/100 ({analysis['stability']['rating'].title()})"],
                    ['Anomalies Detected:', str(analysis['anomaly_count'])],
                    ['Overall Status:', analysis['overall_status'].upper()]
                ]

                table = Table(data, colWidths=[2.5*inch, 3.5*inch])
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4)
                ]))

                elements.append(table)

                # Recommendation
                if analysis['recommendation']:
                    rec_para = Paragraph(f"<b>Recommendation:</b> {analysis['recommendation']}",
                                       self.styles['Normal'])
                    elements.append(rec_para)

                elements.append(Spacer(1, 0.1*inch))

            except Exception as e:
                elements.append(Paragraph(f"Error analyzing {lead_name}: {str(e)}", self.styles['Normal']))

        return elements

    def _create_arrhythmia_section(self, trend: LongitudinalTrend) -> List:
        """Create arrhythmia burden analysis section."""
        elements = []

        elements.append(Paragraph("Arrhythmia Burden Analysis", self.styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))

        try:
            analysis = ArrhythmiaAnalyzer.calculate_burden_statistics(trend)

            if 'error' not in analysis:
                # Burden metrics table
                data = [
                    ['Current Burden:', f"{analysis['current_burden']:.1f}%"],
                    ['Mean Burden:', f"{analysis['mean_burden']:.1f}%"],
                    ['Maximum Burden:', f"{analysis['max_burden']:.1f}%"],
                    ['Trend Direction:', analysis['trend']['direction'].title()],
                    ['Classification:', analysis['classification']['type'].title()],
                    ['Severity:', analysis['classification']['severity'].upper()]
                ]

                table = Table(data, colWidths=[2.5*inch, 3.5*inch])
                table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 6)
                ]))

                elements.append(table)
                elements.append(Spacer(1, 0.1*inch))

                # Recommendation
                recommendation = ArrhythmiaAnalyzer.get_recommendation(analysis)
                rec_para = Paragraph(f"<b>Recommendation:</b> {recommendation}", self.styles['Recommendation'])
                elements.append(rec_para)

        except Exception as e:
            elements.append(Paragraph(f"Error analyzing arrhythmia: {str(e)}", self.styles['Normal']))

        return elements
