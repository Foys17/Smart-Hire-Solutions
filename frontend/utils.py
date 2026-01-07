import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_ats_cv(data):
    """
    Generates a clean, simple PDF optimized for ATS parsing.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch
    )

    styles = getSampleStyleSheet()
    story = []

    # --- CUSTOM STYLES ---
    # Name: Large, Bold, Center
    style_name = ParagraphStyle(
        'Name', parent=styles['Heading1'], 
        fontSize=18, spaceAfter=6, alignment=1 # Center
    )
    # Contact: Small, Center
    style_contact = ParagraphStyle(
        'Contact', parent=styles['Normal'], 
        fontSize=10, alignment=1, spaceAfter=12
    )
    # Section Header: Bold, Uppercase, border bottom effect (simulated by HR)
    style_header = ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'], 
        fontSize=12, spaceBefore=12, spaceAfter=6, 
        textTransform='uppercase', textColor=colors.black
    )
    # Body Text: Clean, legible
    style_body = ParagraphStyle(
        'Body', parent=styles['Normal'], 
        fontSize=10, leading=14, spaceAfter=6
    )

    # 1. HEADER (Name & Contact)
    story.append(Paragraph(data['full_name'], style_name))
    
    contact_parts = [data['email'], data['phone'], data['location']]
    if data.get('linkedin'):
        contact_parts.append(data['linkedin'])
    contact_text = " | ".join(filter(None, contact_parts))
    story.append(Paragraph(contact_text, style_contact))
    
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=12))

    # 2. SUMMARY
    if data.get('summary'):
        story.append(Paragraph("Professional Summary", style_header))
        story.append(Paragraph(data['summary'], style_body))

    # 3. SKILLS
    if data.get('skills'):
        story.append(Paragraph("Skills", style_header))
        story.append(Paragraph(data['skills'], style_body))

    # 4. EXPERIENCE
    if data.get('experience'):
        story.append(Paragraph("Work Experience", style_header))
        # Preserving line breaks for structure
        exp_text = data['experience'].replace('\n', '<br/>')
        story.append(Paragraph(exp_text, style_body))

    # 5. EDUCATION
    if data.get('education'):
        story.append(Paragraph("Education", style_header))
        edu_text = data['education'].replace('\n', '<br/>')
        story.append(Paragraph(edu_text, style_body))

    # 6. PROJECTS
    if data.get('projects'):
        story.append(Paragraph("Key Projects", style_header))
        proj_text = data['projects'].replace('\n', '<br/>')
        story.append(Paragraph(proj_text, style_body))

    doc.build(story)
    buffer.seek(0)
    return buffer