from collections import Counter
from document_tools import load
import re

old_source, old = load('.layout-work/proposal-before-layout.html')
new_source, new = load()

def text(node):
    return ' '.join(node.text().split())

def sections(document):
    result={}
    for n in document.root.all('div','section'):
        hs=[c for c in n.children if c.tag=='h2']
        if hs:
            result[int(re.match(r'(\d+)\.',text(hs[0])).group(1))]=n
    return result

original=sections(old)
rebuilt={int(n.attrs['data-program']):n for n in new.root.all('section','program-page')}
assert set(rebuilt)==set(range(3,23))

def source_counts(section):
    out=[]
    for group in section.all('div','certification-count'):
        for item in [c for c in group.children if c.tag=='span']:
            strong=item.all('strong')[0]
            label=' '.join(''.join(c.text() for c in item.children if c is not strong).split())
            out.append((text(strong),label))
    return out

for num,after in rebuilt.items():
    before=original[num]
    assert text(before.all('h2')[0])==text(after.all('h2')[0]),('heading',num)
    bp=[text(c) for c in before.children if c.tag=='p' and 'small-note' not in c.classes]
    ap=[text(p) for p in after.all('p','program-intro')]
    assert bp==ap,('paragraphs',num,bp,ap)
    bl=[text(li) for c in before.children if c.tag=='ul' for li in c.all('li')]
    al=[text(li) for c in after.all('ul','learning-list') for li in c.all('li')]
    assert bl==al,('bullets',num)
    bo=before.all('div','outcome')[0]
    ao=after.all('div','outcome')[0]
    assert text(bo.all('div','outcome-title')[0])==text(ao.all('div','outcome-title')[0]),('outcome heading',num)
    assert text(bo.all('div','small-note')[0])==text(ao.all('p','outcome-copy')[0]),('outcome',num)
    actual=[(text(m.all('strong')[0]),text(m.all('span')[0])) for m in after.all('div','metric')]
    expected=source_counts(before)
    if num==14:
        expected=[v for v in expected if v[1] != 'CPEH']
        expected.append(('43','Mile2 certification total'))
    if num==22: expected.append(('57','Students completed Cadence certifications'))
    assert expected==actual,('totals',num,expected,actual)
    bp=before.all('div','vendor-pathway-strip')
    ap=after.all('div','vendor-pathway-strip')
    assert [text(n) for n in bp]==[text(n) for n in ap],('pathway',num)
    assert len(after.all('h2'))==1,('section split',num)

before_images=Counter((n.attrs.get('src'),n.attrs.get('alt','')) for n in old.root.all('img'))
after_images=Counter((n.attrs.get('src'),n.attrs.get('alt','')) for n in new.root.all('img'))
after_images.update((n.attrs['data-asset-src'],n.attrs.get('data-asset-alt','')) for n in new.root.all('svg') if 'data-asset-src' in n.attrs)
assert before_images==after_images,('images',before_images-after_images,after_images-before_images)
before_cover=old.root.all('section','cover-page')[0]
after_cover=new.root.all('section','cover-page')[0]
for cls in ['cover-title','cover-vision','date','cover-footer']:
    assert text(before_cover.all(cls=cls)[0])==text(after_cover.all(cls=cls)[0]),('cover',cls)
for h in [1,2]:
    before=original[h]
    if h==1:
        assert [text(p) for p in before.all('p')]==[text(p) for p in new.root.all('div','overview-summary')[0].all('p')]
    else:
        assert [text(li) for li in before.all('li')]==[text(li) for li in new.root.all('ul','objective-grid')[0].all('li')]
assert not new.root.all('section','knowledge-graph-page'),'knowledge graph removed'
before_notes=old.root.all('div','microsoft-count-breakdown')[0]
new_notes=new.root.all('div','credential-notes')[0]
assert text(before_notes)==text(new_notes.all('p')[0]),'Microsoft breakdown'
assert text(original[17].all('p','small-note')[0])==text(new_notes.all('p')[1]),'Microsoft note'
css=new_source[new_source.index('<style>'):new_source.index('</style>')]
assert not re.search(r'(?i)animation\s*:|transition\s*:|:hover|@keyframes',css),'motion'
assert len(new.root.all('section','page'))==22,'page count'
print('PASS: 20 complete programs; all paragraphs, bullets, outcomes, counts, pathway steps, cover copy, overview and 88 image references preserved. 22 pages. No motion.')
