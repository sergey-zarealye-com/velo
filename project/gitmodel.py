from project import db

class Version:
    def __init__(self):
        self.versions = ['a', 'b', 'c', 'd', 'e']
        self.edges = """
                        a->b;
                        b->c;
                        b->d;
                        c->e;
                        d->e;
"""
    
    def nodes_def(self, sel, url_prefix='/datasets/select'):
        TPL1 = '%(id)s[URL="%(prefix)s/%(id)s", style="bold"];\n'
        TPL2 = '%(id)s[URL="%(prefix)s/%(id)s"];'
        out = []
        for v in self.versions:
            if v == sel:
                out.append(TPL1 % dict(id=v, prefix=url_prefix))
            else:
                out.append(TPL2 % dict(id=v, prefix=url_prefix))
        return ''.join(out)
    
    def dot_str(self, sel):
        TPL = """digraph "dsvers" {
        %s
        %s
        }"""
        return TPL % (self.nodes_def(sel), self.edges)