# -*- coding: utf-8 -*-
#
# Author: Ingelrest François (Francois.Ingelrest@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# ExtListView v1.6
#
# v1.6:
#   * Added a context menu to column headers allowing users to show/hide columns
#   * Improved sorting a bit
#
# v1.5:
#   * Fixed intermittent improper columns resizing
#
# v1.4:
#   * Replaced TYPE_INT by TYPE_PYOBJECT as the fifth parameter type of extListview-dnd
#       (see http://www.daa.com.au/pipermail/pygtk/2007-October/014311.html)
#   * Prevent sorting rows when the list is empty
#
# v1.3:
#   * Greatly improved speed when sorting a lot of rows
#   * Added support for gtk.CellRendererToggle
#   * Improved replaceContent() method
#   * Added a call to set_cursor() when removing selected row(s)
#   * Added getFirstSelectedRow(), appendRows(), addColumnAttribute(), unselectAll() and selectAll() methods
#   * Set expand to False when calling pack_start()
#
# v1.2:
#   * Fixed D'n'D reordering bugs
#   * Improved code for testing the state of the keys for mouse clicks
#   * Added quite a few new methods (replaceContent, hasMarkAbove, hasMarkUnder, __len__, iterSelectedRows, iterAllRows)
#
#  v1.1:
#   * Added a call to set_cursor() when unselecting all rows upon clicking on the empty area
#   * Sort indicators are now displayed whenever needed

from gobject import SIGNAL_RUN_LAST
from gobject import TYPE_BOOLEAN
from gobject import TYPE_INT
from gobject import TYPE_NONE
from gobject import TYPE_PYOBJECT
from gobject import TYPE_STRING
from gobject import signal_new
import gtk
from gtk import gdk
import random


# Internal d'n'd (reordering)
DND_REORDERING_ID   = 1024
DND_INTERNAL_TARGET = ('extListview-internal', gtk.TARGET_SAME_WIDGET, DND_REORDERING_ID)


# Custom signals
signal_new('extlistview-dnd', gtk.TreeView, SIGNAL_RUN_LAST, TYPE_NONE, (gdk.DragContext, TYPE_INT, TYPE_INT, gtk.SelectionData, TYPE_INT, TYPE_PYOBJECT))
signal_new('extlistview-modified', gtk.TreeView, SIGNAL_RUN_LAST, TYPE_NONE, ())
signal_new('extlistview-button-pressed', gtk.TreeView, SIGNAL_RUN_LAST, TYPE_NONE, (gdk.Event, TYPE_PYOBJECT))
signal_new('extlistview-column-visibility-changed', gtk.TreeView, SIGNAL_RUN_LAST, TYPE_NONE, (TYPE_STRING, TYPE_BOOLEAN))
signal_new('button-press-event', gtk.TreeViewColumn, SIGNAL_RUN_LAST, TYPE_NONE, (gdk.Event,))


class ExtListViewColumn(gtk.TreeViewColumn):
    """
        TreeViewColumn does not signal right-click events, and we need them
        This subclass is equivalent to TreeViewColumn, but it signals these events

        Most of the code of this class comes from Quod Libet (http://www.sacredchao.net/quodlibet)
    """

    def __init__(self, title=None, cell_renderer=None, ** args):
        """ Constructor, see gtk.TreeViewColumn """
        gtk.TreeViewColumn.__init__(self, title, cell_renderer, ** args)
        label = gtk.Label(title)
        self.set_widget(label)
        label.show()
        label.__realize = label.connect('realize', self.onRealize)


    def onRealize(self, widget):
        widget.disconnect(widget.__realize)
        del widget.__realize
        button = widget.get_ancestor(gtk.Button)
        if button is not None:
            button.connect('button-press-event', self.onButtonPressed)


    def onButtonPressed(self, widget, event):
        self.emit('button-press-event', event)


class ExtListView(gtk.TreeView):


    def __init__(self, columns, sortable=True, dndTargets=[], useMarkup=False, canShowHideColumns=True):
        """
            If sortable is True, the user can click on headers to sort the contents of the list

            The d'n'd targets are the targets accepted by the list (e.g., [('text/uri-list', 0, 0)])
            Note that for the latter, the identifier 1024 must not be used (internally used for reordering)

            If useMarkup is True, the 'markup' attributes is used instead of 'text' for CellRendererTexts
        """
        gtk.TreeView.__init__(self)

        self.selection = self.get_selection()

        # Sorting rows
        self.sortLastCol     = None   # The last column used for sorting (needed to switch between ascending/descending)
        self.sortAscending   = True   # Ascending or descending order
        self.sortColCriteria = {}     # For each column, store the tuple of indexes used to sort the rows

        # Default configuration for this list
        self.set_rules_hint(True)
        self.set_headers_visible(True)
        self.selection.set_mode(gtk.SELECTION_MULTIPLE)

        # Create the columns
        nbEntries = 0
        dataTypes = []
        for (title, renderers, sortIndexes, expandable, visible) in columns:
            if title is None:
                nbEntries += len(renderers)
                dataTypes += [renderer[1] for renderer in renderers]
            else:
                column = ExtListViewColumn(title)
                column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
                column.set_expand(expandable)
                column.set_visible(visible)
                if canShowHideColumns:
                    column.connect('button-press-event', self.onColumnHeaderClicked)
                self.append_column(column)

                if sortable:
                    column.set_clickable(True)
                    column.connect('clicked', self.__sortRows)
                    self.sortColCriteria[column] = sortIndexes

                for (renderer, type) in renderers:
                    nbEntries += 1
                    dataTypes.append(type)
                    column.pack_start(renderer, False)
                    if   isinstance(renderer, gtk.CellRendererToggle): column.add_attribute(renderer, 'active', nbEntries-1)
                    elif isinstance(renderer, gtk.CellRendererPixbuf): column.add_attribute(renderer, 'pixbuf', nbEntries-1)
                    elif isinstance(renderer, gtk.CellRendererText):
                        if useMarkup: column.add_attribute(renderer, 'markup', nbEntries-1)
                        else:         column.add_attribute(renderer, 'text', nbEntries-1)

        # Mark management
        self.markedRow  = None
        self.markColumn = len(dataTypes)
        dataTypes.append(TYPE_BOOLEAN)     # When there's no other solution, this additional entry helps in finding the marked row

        # Create the ListStore associated with this tree
        self.store = gtk.ListStore(*dataTypes)
        self.set_model(self.store)

        # Drag'n'drop management
        self.dndContext    = None
        self.dndTargets    = dndTargets
        self.motionEvtId   = None
        self.dndStartPos   = None
        self.dndReordering = False

        if len(dndTargets) != 0:
            self.enable_model_drag_dest(dndTargets, gdk.ACTION_DEFAULT)

        self.connect('drag-begin', self.onDragBegin)
        self.connect('drag-motion', self.onDragMotion)
        self.connect('button-press-event', self.onButtonPressed)
        self.connect('drag-data-received', self.onDragDataReceived)
        self.connect('button-release-event', self.onButtonReleased)

        # Show the list
        self.show()


    # --== Miscellaneous ==--


    def __getIterOnSelectedRows(self):
        """ Return a list of iterators pointing to the selected rows """
        return [self.store.get_iter(path) for path in self.selection.get_selected_rows()[1]]


    def addColumnAttribute(self, colIndex, renderer, attribute, value):
        """ Add a new attribute to the given column """
        self.get_column(colIndex).add_attribute(renderer, attribute, value)


    # --== Mark management ==--


    def hasMark(self):
        """ True if a mark has been set """
        return self.markedRow is not None


    def hasMarkAbove(self, index):
        """ True if a mark is set and is above the given index """
        return self.markedRow is not None and self.markedRow > index


    def hasMarkUnder(self, index):
        """ True if a mark is set and is undex the given index """
        return self.markedRow is not None and self.markedRow < index


    def clearMark(self):
        """ Remove the mark """
        if self.markedRow is not None:
            self.setItem(self.markedRow, self.markColumn, False)
            self.markedRow = None


    def getMark(self):
        """ Return the index of the marked row """
        return self.markedRow


    def setMark(self, rowIndex):
        """ Put the mark on the given row, it will move with the row itself (e.g., D'n'D) """
        self.clearMark()
        self.markedRow = rowIndex
        self.setItem(rowIndex, self.markColumn, True)


    def __findMark(self):
        """ Linear search for the marked row -- To be used only when there's no other solution """
        iter = self.store.get_iter_first()

        while iter is not None:
            if self.store.get_value(iter, self.markColumn) == True:
                self.markedRow = self.store.get_path(iter)[0]
                break
            iter = self.store.iter_next(iter)


    # --== Sorting content ==--


    def __resetSorting(self):
        """ Reset sorting such that the next column click will result in an ascending sorting """
        if self.sortLastCol is not None:
            self.sortLastCol.set_sort_indicator(False)
            self.sortLastCol = None


    def __cmpRows(self, row1, row2, criteria, ascending):
        """ Compare two rows based on the given criteria, the latter being a tuple of the indexes to use for the comparison """
        # Sorting on the first criterion may be done either ascending or descending
        criterion = criteria[0]
        result    = cmp(row1[criterion], row2[criterion])

        if result != 0:
            if ascending: return result
            else:         return -result

        # For subsequent criteria, the order is always ascending
        for criterion in criteria[1:]:
            result = cmp(row1[criterion], row2[criterion])

            if result != 0:
                return result

        return 0


    def __sortRows(self, column):
        """ Sort the rows """
        if len(self.store) == 0:
            return

        if self.sortLastCol is not None:
            self.sortLastCol.set_sort_indicator(False)

        # Find how sorting must be performed
        if self.sortLastCol == column:
            self.sortAscending = not self.sortAscending
        else:
            self.sortLastCol   = column
            self.sortAscending = True

        # Dump the rows, sort them, and reorder the list
        rows     = [tuple(r) + (i, ) for i, r in enumerate(self.store)]
        criteria = self.sortColCriteria[column]
        rows.sort(lambda r1, r2: self.__cmpRows(r1, r2, criteria, self.sortAscending))
        self.store.reorder([r[-1] for r in rows])

        # Move the mark if needed
        if self.markedRow is not None:
            self.__findMark()

        column.set_sort_indicator(True)
        if self.sortAscending: column.set_sort_order(gtk.SORT_ASCENDING)
        else:                  column.set_sort_order(gtk.SORT_DESCENDING)

        self.emit('extlistview-modified')


    # --== Selection ==--


    def unselectAll(self):
        """ Unselect all rows """
        self.selection.unselect_all()


    def selectAll(self):
        """ Select all rows """
        self.selection.select_all()


    def getSelectedRowsCount(self):
        """ Return how many rows are currently selected """
        return self.selection.count_selected_rows()


    def getSelectedRows(self):
        """ Return all selected row(s) """
        return [tuple(self.store[path])[:-1] for path in self.selection.get_selected_rows()[1]]


    def getFirstSelectedRow(self):
        """ Return only the first selected row """
        return tuple(self.store[self.selection.get_selected_rows()[1][0]])[:-1]


    def getFirstSelectedRowIndex(self):
        """ Return the index of the first selected row """
        return self.selection.get_selected_rows()[1][0][0]


    def iterSelectedRows(self):
        """ Iterate on all selected row(s) """
        for path in self.selection.get_selected_rows()[1]:
            yield tuple(self.store[path])[:-1]


    # --== Retrieving content / Iterating on content ==--


    def __len__(self):
        """ Return how many rows are stored in the list """
        return len(self.store)


    def getCount(self):
        """ Return how many rows are stored in the list """
        return len(self.store)


    def getRow(self, rowIndex):
        """ Return the given row """
        return tuple(self.store[rowIndex])[:-1]


    def getAllRows(self):
        """ Return all rows """
        return [tuple(row)[:-1] for row in self.store]


    def iterAllRows(self):
        """ Iterate on all rows """
        for row in self.store:
            yield tuple(row)[:-1]


    def getItem(self, rowIndex, colIndex):
        """ Return the value of the given item """
        return self.store.get_value(self.store.get_iter(rowIndex), colIndex)


    # --== Adding/removing/modifying content ==--


    def clear(self):
        """ Remove all rows from the list """
        self.__resetSorting()
        self.clearMark()
        self.store.clear()
        # This fixes the problem of columns sometimes not resizing correctly
        self.resize_children()


    def setItem(self, rowIndex, colIndex, value):
        """ Change the value of the given item """
        # Check if changing that item may change the sorting: if so, reset sorting
        if self.sortLastCol is not None and colIndex in self.sortColCriteria[self.sortLastCol]:
            self.__resetSorting()
        self.store.set_value(self.store.get_iter(rowIndex), colIndex, value)


    def removeSelectedRows(self):
        """ Remove the selected row(s) """
        self.freeze_child_notify()
        for iter in self.__getIterOnSelectedRows():
            # Move the mark if needed
            if self.markedRow is not None:
                currentPath = self.store.get_path(iter)[0]
                if   currentPath < self.markedRow:  self.markedRow -= 1
                elif currentPath == self.markedRow: self.markedRow  = None
            # Remove the current row
            if   self.store.remove(iter): self.set_cursor(self.store.get_path(iter))
            elif len(self.store) != 0:    self.set_cursor(len(self.store)-1)
        self.thaw_child_notify()
        if len(self.store) == 0:
            self.set_cursor(0)
            self.__resetSorting()
        # This fixes the problem of columns sometimes not resizing correctly
        self.resize_children()
        self.emit('extlistview-modified')


    def cropSelectedRows(self):
        """ Remove all rows but the selected ones """
        pathsList = self.selection.get_selected_rows()[1]
        self.freeze_child_notify()
        self.selection.select_all()
        for path in pathsList:
            self.selection.unselect_path(path)
        self.removeSelectedRows()
        self.selection.select_all()
        self.thaw_child_notify()


    def insertRows(self, rows, position=None):
        """ Insert or append (if position is None) some rows to the list """
        if len(rows) == 0:
            return

        # Insert the additional column used for the mark management
        if type(rows[0]) is tuple: rows[:] = [row + (False, ) for row in rows]
        else:                      rows[:] = [row + [False] for row in rows]

        # Move the mark if needed
        if self.markedRow is not None and position is not None and position <= self.markedRow:
            self.markedRow += len(rows)

        # Insert rows
        self.freeze_child_notify()
        if position is None:
            for row in rows:
                self.store.append(row)
        else:
            for row in rows:
                self.store.insert(position, row)
                position += 1
        self.thaw_child_notify()
        self.__resetSorting()
        self.emit('extlistview-modified')


    def appendRows(self, rows):
        """ Helper function, equivalent to insertRows(rows, None) """
        self.insertRows(rows, None)


    def replaceContent(self, rows):
        """ Replace the content of the list with the given rows """
        self.freeze_child_notify()
        self.set_model(None)
        self.clear()
        self.appendRows(rows)
        self.set_model(self.store)
        self.thaw_child_notify()


    def shuffle(self):
        """ Shuffle the content of the list """
        order = xrange(len(self.store))
        random.shuffle(order)
        self.store.reorder(order)

        # Move the mark if needed
        if self.markedRow is not None:
            self.__findMark()

        self.__resetSorting()
        self.emit('extlistview-modified')


    # --== D'n'D management ==--


    def enableDNDReordering(self):
        """ Enable the use of Drag'n'Drop to reorder the list """
        self.dndReordering = True
        self.dndTargets.append(DND_INTERNAL_TARGET)
        self.enable_model_drag_dest(self.dndTargets, gdk.ACTION_DEFAULT)


    def __isDropAfter(self, pos):
        """ Helper function, True if pos is gtk.TREE_VIEW_DROP_AFTER or gtk.TREE_VIEW_DROP_INTO_OR_AFTER """
        return pos == gtk.TREE_VIEW_DROP_AFTER or pos == gtk.TREE_VIEW_DROP_INTO_OR_AFTER


    def __moveSelectedRows(self, x, y):
        """ Internal function used for drag'n'drop """
        iterList = self.__getIterOnSelectedRows()
        dropInfo = self.get_dest_row_at_pos(int(x), int(y))

        if dropInfo is None:
            pos, path = gtk.TREE_VIEW_DROP_INTO_OR_AFTER, len(self.store) - 1
        else:
            pos, path = dropInfo[1], dropInfo[0][0]
            if self.__isDropAfter(pos) and path < len(self.store)-1:
                pos   = gtk.TREE_VIEW_DROP_INTO_OR_BEFORE
                path += 1

        self.freeze_child_notify()
        for srcIter in iterList:
            srcPath = self.store.get_path(srcIter)[0]

            if self.__isDropAfter(pos):
                dstIter = self.store.insert_after(self.store.get_iter(path), self.store[srcIter])
            else:
                dstIter = self.store.insert_before(self.store.get_iter(path), self.store[srcIter])
                if path == srcPath:
                    path += 1

            self.store.remove(srcIter)
            dstPath = self.store.get_path(dstIter)[0]

            if srcPath > dstPath:
                path += 1

            if self.markedRow is not None:
                if   srcPath == self.markedRow:                              self.markedRow  = dstPath
                elif srcPath < self.markedRow and dstPath >= self.markedRow: self.markedRow -= 1
                elif srcPath > self.markedRow and dstPath <= self.markedRow: self.markedRow += 1
        self.thaw_child_notify()
        self.__resetSorting()
        self.emit('extlistview-modified')


    # --== GTK Handlers ==--


    def onButtonPressed(self, tree, event):
        """ A mouse button has been pressed """
        retVal   = False
        pathInfo = self.get_path_at_pos(int(event.x), int(event.y))

        if pathInfo is None: path = None
        else:                path = pathInfo[0]

        if event.button == 1 or event.button == 3:
            if path is None:
                self.selection.unselect_all()
                tree.set_cursor(len(self.store))
            else:
                if self.dndReordering and self.motionEvtId is None and event.button == 1:
                    self.dndStartPos = (int(event.x), int(event.y))
                    self.motionEvtId = gtk.TreeView.connect(self, 'motion-notify-event', self.onMouseMotion)

                stateClear = not (event.state & (gdk.SHIFT_MASK | gdk.CONTROL_MASK))

                if stateClear and not self.selection.path_is_selected(path):
                    self.selection.unselect_all()
                    self.selection.select_path(path)
                else:
                    retVal = (stateClear and self.getSelectedRowsCount() > 1 and self.selection.path_is_selected(path))

        self.emit('extlistview-button-pressed', event, path)

        return retVal


    def onButtonReleased(self, tree, event):
        """ A mouse button has been released """
        if self.motionEvtId is not None:
            self.disconnect(self.motionEvtId)
            self.dndContext  = None
            self.motionEvtId = None

            if len(self.dndTargets) != 0:
                self.enable_model_drag_dest(self.dndTargets, gdk.ACTION_DEFAULT)

        stateClear = not (event.state & (gdk.SHIFT_MASK | gdk.CONTROL_MASK))

        if stateClear and event.state & gdk.BUTTON1_MASK and self.getSelectedRowsCount() > 1:
            pathInfo = self.get_path_at_pos(int(event.x), int(event.y))
            if pathInfo is not None:
                self.selection.unselect_all()
                self.selection.select_path(pathInfo[0][0])


    def onMouseMotion(self, tree, event):
        """ The mouse has been moved """
        if self.dndContext is None and self.drag_check_threshold(self.dndStartPos[0], self.dndStartPos[1], int(event.x), int(event.y)):
            self.dndContext = self.drag_begin([DND_INTERNAL_TARGET], gdk.ACTION_COPY, 1, event)


    def onDragBegin(self, tree, context):
        """ A drag'n'drop operation has begun """
        if self.getSelectedRowsCount() == 1: context.set_icon_stock(gtk.STOCK_DND, 0, 0)
        else:                                context.set_icon_stock(gtk.STOCK_DND_MULTIPLE, 0, 0)


    def onDragDataReceived(self, tree, context, x, y, selection, dndId, time):
        """ Some data has been dropped into the list """
        if dndId == DND_REORDERING_ID: self.__moveSelectedRows(x, y)
        else:                          self.emit('extlistview-dnd', context, int(x), int(y), selection, dndId, time)


    def onDragMotion(self, tree, context, x, y, time):
        """ Prevent rows from being dragged *into* other rows (this is a list, not a tree) """
        drop = self.get_dest_row_at_pos(int(x), int(y))

        if drop is not None and (drop[1] == gtk.TREE_VIEW_DROP_INTO_OR_AFTER or drop[1] == gtk.TREE_VIEW_DROP_INTO_OR_BEFORE):
            self.enable_model_drag_dest([('invalid-position', 0, -1)], gdk.ACTION_DEFAULT)
        else:
            self.enable_model_drag_dest(self.dndTargets, gdk.ACTION_DEFAULT)


    def onColumnHeaderClicked(self, column, event):
        """ A column header has been clicked """
        if event.button == 3:
            # Create a menu with a CheckMenuItem per column
            menu            = gtk.Menu()
            nbVisibleItems  = 0
            lastVisibleItem = None
            for column in self.get_columns():
                item = gtk.CheckMenuItem(column.get_title())
                item.set_active(column.get_visible())
                item.connect('toggled', self.onShowHideColumn, column)
                item.show()
                menu.append(item)

                # Count how many columns are visible
                if item.get_active():
                    nbVisibleItems  += 1
                    lastVisibleItem  = item

            # Don't allow the user to hide the only visible column left
            if nbVisibleItems == 1:
                lastVisibleItem.set_sensitive(False)

            menu.popup(None, None, None, event.button, event.get_time())


    def onShowHideColumn(self, menuItem, column):
        """ Switch the visibility of the given column """
        column.set_visible(not column.get_visible())
        self.emit('extlistview-column-visibility-changed', column.get_title(), column.get_visible())
