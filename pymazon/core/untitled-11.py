def flatten(node):
    if node.subnodes:
        for snode in node.subnodes:
            for ssnode in flatten(snode):
                yield ssnode
    yield node
                   
               
class Node(object):
    def __init__(self, id, subnodes=[]):
        self.subnodes = subnodes
        self.id = id
        
    def __str__(self):
        return str(self.id)
        
        
tree = Node(1, [Node(2, [Node(8), Node(9, [Node(10), Node(11)])]), Node(3), Node(4), Node(5, [Node(6), Node(7)])])

flat = flatten(tree)
for f in flat:
    print f