from html.parser import HTMLParser
from html import unescape
from pathlib import Path
import json

VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

class Node:
    def __init__(self, tag='', attrs=None, parent=None, start=0, end=0, value=''):
        self.tag, self.attrs, self.parent = tag, dict(attrs or []), parent
        self.start, self.end, self.value = start, end, value
        self.children = []
    @property
    def classes(self):
        return self.attrs.get('class','').split()
    def all(self, tag=None, cls=None):
        out = []
        for child in self.children:
            if child.tag and (tag is None or child.tag == tag) and (cls is None or cls in child.classes):
                out.append(child)
            out.extend(child.all(tag, cls))
        return out
    def text(self):
        if not self.tag:
            return unescape(self.value)
        return ''.join(child.text() for child in self.children)
    def raw(self, source):
        return source[self.start:self.end]

class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0]
        self.lines += [i+1 for i,c in enumerate(source) if c == '\n']
        self.root = Node('document')
        self.stack = [self.root]
        self.feed(source)
        self.close()
    def position_index(self):
        line, col = self.getpos()
        return self.lines[line-1]+col
    def handle_starttag(self, tag, attrs):
        pos = self.position_index()
        node = Node(tag, attrs, self.stack[-1], pos, pos+len(self.get_starttag_text()))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        pos = self.position_index()
        node = Node(tag, attrs, self.stack[-1], pos, pos+len(self.get_starttag_text()))
        self.stack[-1].children.append(node)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                end = self.source.find('>',self.position_index())+1
                for node in self.stack[i:]:
                    node.end = end
                del self.stack[i:]
                break
    def handle_data(self, value):
        self.stack[-1].children.append(Node(parent=self.stack[-1], value=value))
    def handle_entityref(self, name):
        self.handle_data('&'+name+';')
    def handle_charref(self, name):
        self.handle_data('&#'+name+';')

def load(path='technicalhub_srm_proposal_doc.html'):
    source = Path(path).read_text(encoding='utf-8')
    return source, Document(source)

if __name__ == '__main__':
    source, doc = load()
    for i,page in enumerate(doc.root.all('section','page'),1):
        print('\nPAGE',i, page.attrs.get('class'))
        print('HEADINGS', [h.text().strip() for h in page.all('h2')])
        print('DIRECT', [(n.tag,n.attrs.get('class',''),len(n.all('img'))) for n in page.children if n.tag and n.tag not in ('svg',)])
        print('PHOTOS',[(n.attrs.get('src'),n.attrs.get('class','')) for n in page.all('img') if 'GroupPhotos/' in n.attrs.get('src','')])
