
from pymazon.core.tree_model import TreeModel as PymazonTreeModel
import gtk
import gobject

class TreeModel(gtk.GenericTreeModel, PymazonTreeModel):    
    def __init__(self, parser_list):
        self.create_tree(parser_list)
        gtk.GenericTreeModel.__init__(self)
                 
    def on_get_flags(self):        
        return gtk.TREE_MODEL_ITERS_PERSIST
    
    def on_get_n_columns(self):
        return 3

    def on_get_column_type(self, idx):
        if idx == 0 or idx == 2:
            return gobject.TYPE_STRING
        else:
            return gobject.TYPE_INT

    def on_get_iter(self, path):
        root_idx = path[0]
        if root_idx < 0 or root_idx >= len(self.root_nodes):
            raise ValueError
        node = self.root_nodes[root_idx]
        if len(path) == 1:
            return node
        for i in path[1:]:
            node = node[i]
        return node
    
    def on_get_path(self, rowref):
        path = []        
        while True:
            path.append(rowref.row)
            if not rowref.parent:
                break
            else:
                rowref = rowref.parent
        path.reverse()
        return tuple(path)

    def on_get_value(self, rowref, column):                     
        if column == 0:
            return rowref.elem.data()
        elif column == 1:                    
            return rowref.elem.status()[0]
        elif column == 2:
            return rowref.elem.status()[1]        
                
    def on_iter_next(self, rowref):
        new_row = rowref.row + 1
        if rowref.parent is None:
            parent = self.root_nodes
        else:   
            parent = rowref.parent
        try:
            return parent[new_row]
        except (ValueError, IndexError):
            return None    

    def on_iter_children(self, parent):
        if parent is None:
            parent = self.root_nodes
        try:
            return parent[0]
        except ValueError:
            return None

    def on_iter_has_child(self, rowref):
        if rowref.subnodes:
            return True
        return False

    def on_iter_n_children(self, rowref):
        if rowref is None:
            return len(self.root_nodes)
        return len(iter.subnodes)

    def on_iter_nth_child(self, parent, n):
        if parent is None:
            parent = self.root_nodes
        try:
            return parent[n]
        except ValueError:
            return None

    def on_iter_parent(self, child):
        return child.parent 

    def update_node(self, node):       
        path = self.on_get_path(node)
        self.emit('row-changed', path, self.get_iter(path)) 
        
        

        
