from pathlib import Path
from urllib.parse import unquote
from html import escape
from collections import Counter
from PIL import Image, ImageChops
import re, json, xml.etree.ElementTree as ET
from document_tools import load

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / '.layout-work/proposal-before-layout.html'
TARGET = ROOT / 'technicalhub_srm_proposal_doc.html'
source, doc = load(SOURCE)
pages = doc.root.all('section', 'page')

def inner(n):
    start = source.index('>', n.start) + 1
    end = source.rfind('</', start, n.end)
    return source[start:end]

def clean_text(t):
    return ' '.join(t.split())

def heading(n):
    h = n.all('h2')[0]
    return int(re.match(r'(\d+)\.', h.text()).group(1)), h

def has_parent(n, cls):
    while n.parent:
        n = n.parent
        if cls in n.classes:
            return True
    return False

sections = {}
for n in doc.root.all('div', 'section'):
    if any(c.tag == 'h2' for c in n.children):
        num, h = heading(n)
        sections[num] = n

photos = {n: [] for n in range(3,23)}
photo_only = {4:5, 7:7, 17:17}
for page_no, page in enumerate(pages,1):
    nums = [int(re.match(r'(\d+)\.', h.text()).group(1)) for h in page.all('h2')]
    for image in page.all('img'):
        if 'GroupPhotos/' not in image.attrs.get('src',''):
            continue
        owner = None
        p = image.parent
        while p and p is not page:
            if p.tag == 'div' and 'section' in p.classes and p.all('h2'):
                owner = heading(p)[0]
                break
            p = p.parent
        owner = owner or photo_only.get(page_no) or nums[-1]
        photos[owner].append(image)

asset_cache = {}
def bounds(src):
    if src in asset_cache:
        return asset_cache[src]
    path = ROOT / unquote(src)
    if path.suffix.lower() == '.svg':
        root = ET.parse(path).getroot()
        vb = root.attrib.get('viewBox','').replace(',',' ').split()
        if len(vb) == 4:
            width, height = float(vb[2]), float(vb[3])
        else:
            width = float(re.sub('[^0-9.]','',root.attrib['width']))
            height = float(re.sub('[^0-9.]','',root.attrib['height']))
        value = (width,height,(0,0,width,height))
    else:
        im = Image.open(path).convert('RGBA')
        diff = ImageChops.difference(im.convert('RGB'),Image.new('RGB',im.size,'white')).convert('L')
        mask = ImageChops.multiply(diff.point(lambda p: 255 if p>15 else 0), im.getchannel('A'))
        bb = mask.getbbox() or im.getchannel('A').getbbox() or (0,0,im.width,im.height)
        pad = max(2,round(max(bb[2]-bb[0],bb[3]-bb[1])*.012))
        bb = (max(0,bb[0]-pad),max(0,bb[1]-pad),min(im.width,bb[2]+pad),min(im.height,bb[3]+pad))
        value = (im.width,im.height,(bb[0],bb[1],bb[2]-bb[0],bb[3]-bb[1]))
    asset_cache[src] = value
    return value

def asset(image, role='brand-mark'):
    src = image.attrs['src']
    alt = image.attrs.get('alt','')
    title = image.attrs.get('title',alt)
    width,height,bb = bounds(src)
    viewbox = ' '.join(f'{v:g}' for v in bb)
    return (f'<svg class="{role}" viewBox="{viewbox}" role="img" aria-label="{escape(alt,quote=True)}" '
            f'data-asset-src="{escape(src,quote=True)}" data-asset-alt="{escape(alt,quote=True)}" data-asset-title="{escape(title,quote=True)}" preserveAspectRatio="xMidYMid meet">'
            f'<title>{escape(title)}</title><image href="{escape(src,quote=True)}" x="0" y="0" width="{width:g}" height="{height:g}" /></svg>')

def title(h):
    text = h.text().strip()
    num,name = text.split('. ',1)
    return f'<h2><span class="section-number">{escape(num)}.</span> <span class="section-name">{escape(name)}</span></h2>'

def header(label):
    return f'<header class="page-header"><strong>Technical Hub | SRM University</strong><span>{escape(label)}</span></header>'

def footer(n):
    return f'<footer class="page-footer"><span>SRM AI &amp; Enterprise CoE Initiative</span><span>Page {n:02d}</span></footer>'

def counts(section):
    values=[]
    for group in section.all('div','certification-count'):
        for item in [c for c in group.children if c.tag == 'span']:
            strong=item.all('strong')[0]
            label=clean_text(''.join(c.text() for c in item.children if c is not strong))
            values.append((strong.text().strip(),label))
    if heading(section)[0] == 14:
        values=[v for v in values if v[1] != 'CPEH']
        values.append(('43','Mile2 certification total'))
    if heading(section)[0] == 22:
        values.append(('57','Students completed Cadence certifications'))
    return values

def metric_markup(values):
    if not values: return ''
    return '<div class="metrics">'+''.join(f'<div class="metric"><strong>{escape(v)}</strong><span>{escape(label)}</span></div>' for v,label in values)+'</div>'

def gallery_markup(images):
    if not images: return ''
    names={1:'one',2:'two',4:'four'}
    out=f'<div class="cohort-gallery cohort-gallery--{names[len(images)]}" aria-label="Student group photos">'
    for image in images:
        attrs={k:image.attrs[k] for k in ('src','alt','title') if k in image.attrs}
        out+='<figure class="cohort-photo"><img class="cohort-image" '+ ' '.join(f'{k}="{escape(v,quote=True)}"' for k,v in attrs.items())+'></figure>'
    return out+'</div>'

def program(num):
    n=sections[num]
    h=n.all('h2')[0]
    logo_block=n.all('div','partner-logos')[0]
    logos=logo_block.all('img')
    badges=[i for i in n.all('img') if i not in logos and 'GroupPhotos/' not in i.attrs.get('src','')]
    totals=counts(n)
    pp=photos[num]
    pathway=n.all('div','vendor-pathway-strip')
    mode='program--photos' if pp else 'program--text-only'
    mode+= ' program--pathway' if pathway else ''
    mode+= ' program--gallery4' if len(pp)==4 else ''
    mode+= ' program--openai' if num==4 else ''
    mode+= ' program--microsoft' if num==17 else ''
    mode+= ' program--no-credentials' if not badges and not totals else ''
    out=f'<section class="page program-page {mode}" data-program="{num}">'+header('Industry-certified learning pathways')+'<div class="program-content">'+title(h)
    out+='<div class="brand-row">'+''.join('<div class="brand-cell">'+asset(i)+'</div>' for i in logos)+'</div>'
    out+='<div class="learning-content">'
    for c in n.children:
        if c.tag == 'p' and 'small-note' not in c.classes:
            out+='<p class="program-intro">'+inner(c)+'</p>'
        elif c.tag == 'ul':
            out+='<ul class="learning-list">'+''.join('<li><span class="learning-copy">'+inner(li)+'</span></li>' for li in c.children if li.tag == 'li')+'</ul>'
    out+='</div>'
    if badges or totals:
        classes={4:' credential-strip--four',5:' credential-strip--five'}.get(len(badges),'')
        out+='<div class="credential-strip'+classes+'">'
        if badges: out+='<div class="badge-row">'+''.join(asset(i,'badge-mark') for i in badges)+'</div>'
        out+=metric_markup(totals)+'</div>'
    notes=[]
    for p in n.all('p'):
        if p.parent is n and 'small-note' not in p.classes: continue
        if has_parent(p,'outcome'): continue
        notes.append(inner(p))
    for b in n.all('div','microsoft-count-breakdown'):
        notes.insert(0,inner(b))
    if notes: out+='<div class="credential-notes">'+''.join('<p>'+x+'</p>' for x in notes)+'</div>'
    outcome=n.all('div','outcome')
    if outcome:
        oc=outcome[0]
        out+='<div class="outcome"><div class="outcome-title">'+inner(oc.all('div','outcome-title')[0])+'</div><p class="outcome-copy">'+inner(oc.all('div','small-note')[0])+'</p></div>'
    if pathway: out+=pathway[0].raw(source)
    out+=gallery_markup(pp)
    out+='</div>'+footer(num)+'</section>'
    return out

cover=pages[0]
cover_images=cover.all('img')
def cover_inner(cls):
    n=cover.all(cls=cls)[0]
    return inner(n)
body='<section class="page cover-page"><div class="cover-brands">'+''.join('<div class="cover-brand">'+asset(i)+'</div>' for i in cover_images)+'</div>'
body+='<div class="cover-title">'+cover_inner('cover-title')+'</div>'
body+='<div class="cover-vision">'+cover_inner('cover-vision')+'</div>'
body+='<div class="date">'+cover_inner('date')+'</div>'
body+='<div class="cover-footer">'+cover_inner('cover-footer')+'</div></section>'
body+='<section class="page overview-page">'+header('Proposal overview')+'<div class="overview-content">'
body+='<div class="overview-summary">'+title(sections[1].all('h2')[0])+''.join(c.raw(source) for c in sections[1].children if c.tag=='p')+'</div>'
obj=sections[2].all('ul')[0]
body+='<div class="overview-objectives">'+title(sections[2].all('h2')[0])+'<ul class="objective-grid">'+inner(obj)+'</ul></div>'
body+='</div>'+footer(2)+'</section>'
body+='\n'.join(program(n) for n in range(3,23))
css=(ROOT/'.layout-work/proposal.css').read_text(encoding='utf-8')
html='<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SRM AI &amp; Enterprise Centers of Excellence — Technical Hub &amp; SRM University</title>\n<style>\n'+css+'\n</style></head><body>\n'+body+'\n</body></html>\n'
TARGET.write_text(html,encoding='utf-8')

old=Counter(i.attrs['src'] for i in doc.root.all('img'))
_,rebuilt=load(TARGET)
new=Counter(i.attrs['src'] for i in rebuilt.root.all('img'))
new.update(i.attrs['data-asset-src'] for i in rebuilt.root.all('svg') if 'data-asset-src' in i.attrs)
assert old==new,(old-new,new-old)
manifest={'programs':[], 'image_count':sum(old.values()),'photo_count':sum(len(v) for v in photos.values())}
for num in range(3,23):
    n=sections[num]
    manifest['programs'].append({'number':num,'heading':n.all('h2')[0].text().strip(),'photos':[i.attrs['src'] for i in photos[num]],'counts':counts(n)})
(ROOT/'.layout-work/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'pages':len(rebuilt.root.all('section','page')),'programs':20,'images_preserved':sum(old.values()),'photos':manifest['photo_count']},indent=2))
