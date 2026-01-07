import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def generate_ats_cv(data):
    """
    Generates a clean, simple PDF optimized for ATS parsing.
    Updated to handle structured lists for Exp, Edu, and Projects.
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
    style_name = ParagraphStyle(
        'Name', parent=styles['Heading1'], 
        fontSize=18, spaceAfter=6, alignment=1 
    )
    style_contact = ParagraphStyle(
        'Contact', parent=styles['Normal'], 
        fontSize=10, alignment=1, spaceAfter=12
    )
    style_header = ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'], 
        fontSize=12, spaceBefore=12, spaceAfter=6, 
        textTransform='uppercase', textColor=colors.black
    )
    style_body = ParagraphStyle(
        'Body', parent=styles['Normal'], 
        fontSize=10, leading=14, spaceAfter=6
    )
    style_item_header = ParagraphStyle(
        'ItemHeader', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', leading=14
    )

    # 1. HEADER
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

    # 4. EXPERIENCE (Dynamic List)
    if data.get('experience_list'):
        story.append(Paragraph("Work Experience", style_header))
        for item in data['experience_list']:
            # Header: Job Title | Company | Dates
            parts = [item['title'], item['company'], item['dates']]
            header_text = " | ".join(filter(None, parts))
            story.append(Paragraph(header_text, style_item_header))
            
            # Position/Description
            if item.get('position'):
                desc = item['position'].replace('\n', '<br/>')
                story.append(Paragraph(desc, style_body))
            story.append(Spacer(1, 4))

    # 5. EDUCATION (Dynamic List)
    if data.get('education_list'):
        story.append(Paragraph("Education", style_header))
        for item in data['education_list']:
            # Degree | College | Dates
            parts = [item['degree'], item['college'], item['dates']]
            text = " | ".join(filter(None, parts))
            story.append(Paragraph(text, style_body))

    # 6. PROJECTS (Dynamic List)
    if data.get('projects_list'):
        story.append(Paragraph("Key Projects", style_header))
        for item in data['projects_list']:
            # Name | Tech
            header_parts = [item['name']]
            if item.get('tech'):
                header_parts.append(f"({item['tech']})")
            
            header_text = " ".join(header_parts)
            story.append(Paragraph(header_text, style_item_header))
            
            # Description
            if item.get('desc'):
                story.append(Paragraph(item['desc'].replace('\n', '<br/>'), style_body))
            
            # Link
            if item.get('link'):
                link_text = f"<a href='{item['link']}' color='blue'>{item['link']}</a>"
                story.append(Paragraph(link_text, style_body))
            
            story.append(Spacer(1, 4))

    doc.build(story)
    buffer.seek(0)
    return buffer