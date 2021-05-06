# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
Full credit to White Russsian, most of this was shamelessly stolen from him: https://github.com/Eve-PySpy/PySpy

This is the GUI file, it has an App class which just displays the Frame, and the main Frame class which contains all
the details on how the GUI is made. The GUI contains numerous methods for various user interaction responses.
"""
import aboutdialog
import config
import eveDB
import logging
import os
import shutil
import sortarray
import statusmsg
import webbrowser
import wx
import wx.grid as WXG
import wx.lib.agw.persist as pm

Logger = logging.getLogger(__name__)


class Frame(wx.Frame):
    """
    Just an extension of wx.Frame, a whole lot going on in here.
    """
    def __init__(self, *args, **kwds):
        """
        Setting a lot of stuff, you know the __init__ deal, stiff drink recommended before reading
        """
        # Persistent Options
        self.options = config.OPTIONS_OBJECT

        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE  # wx.RESIZE_BORDER
        wx.Frame.__init__(self, *args, **kwds)
        self.SetName("Main Window")

        self.Font = self.Font.Scaled(self.options.Get("FontScale", 1))

        # Set stay on-top unless user deactivated it
        if self.options.Get("StayOnTop", True):
            self.ToggleWindowStyle(wx.STAY_ON_TOP)

        # Set parameters for columns
        self.columns = (
            # Index, Heading, Format, Default Width, Can Toggle, Default Show, Menu Name, Outlist Column
            [0, "ID", wx.ALIGN_LEFT, 0, False, False, "", 'pilot_id'],
            [1, "Warning", wx.ALIGN_LEFT, 80, True, True, "Warning", 'warning'],
            [2, "Character", wx.ALIGN_LEFT, 80, False, True, "Character", 'pilot_name'],
            [3, "Corporation", wx.ALIGN_LEFT, 80, True, True, "Corporation", 'corp_name'],
            [4, "Alliance", wx.ALIGN_LEFT, 80, True, True, "Alliance", 'alliance_name'],
            [5, "Cyno", wx.ALIGN_LEFT, 80, True, True, "Cyno Use", 'cyno'],
            [6, "Avg. Gang", wx.ALIGN_LEFT, 80, True, True, "Average Gang", 'avg_gang'],
            [7, "Avg. Fleet", wx.ALIGN_LEFT, 80, True, True, "Average Fleet Size", 'avg_10'],
            [8, "Timezone", wx.ALIGN_LEFT, 80, True, True, "Timezone", "timezone"],
            [9, "Top Ships", wx.ALIGN_LEFT, 80, True, True, "Top Ships", 'top_ships'],
            [10, "Top Gang Ships", wx.ALIGN_LEFT, 80, True, True, "Top Gang Ships", 'top_gang_ships'],
            [11, "Top Fleet Ships", wx.ALIGN_LEFT, 80, True, True, "Top Fleet Ships", 'top_10_ships'],
            [12, "Gate Kills", wx.ALIGN_LEFT, 80, True, True, "Gatecamping", 'boy_scout'],
            [13, "Super", wx.ALIGN_LEFT, 40, True, True, "Super Kills", 'super'],
            [14, "Titan", wx.ALIGN_LEFT, 40, True, True, "Titan Kills", 'titan'],
            [15, "Capital", wx.ALIGN_LEFT, 80, True, True, "Capital Use", 'capital_use'],
            [16, "Blops", wx.ALIGN_LEFT, 80, True, True, "Blops Use", 'blops_use'],
            [17, "Top Regions", wx.ALIGN_LEFT, 80, True, True, "Top Regions", 'top_regions'],
            [18, "", None, 1, False, True, "", 1]  # Need for _stretchLastCol()
            )

        # Define the menu bar and menu items
        self.menubar = wx.MenuBar()
        self.menubar.SetName("Menubar")
        if os.name == "nt":  # For Windows
            self.file_menu = wx.Menu()
            self.file_about = self.file_menu.Append(wx.ID_ANY, '&About\tCTRL+A')
            self.file_menu.Bind(wx.EVT_MENU, self._openAboutDialog, self.file_about)
            self.file_quit = self.file_menu.Append(wx.ID_ANY, 'Quit HawkEye')
            self.file_menu.Bind(wx.EVT_MENU, self.OnQuit, self.file_quit)
            self.menubar.Append(self.file_menu, 'File')
        if os.name == "posix":  # For macOS
            self.help_menu = wx.Menu()
            self.help_about = self.help_menu.Append(wx.ID_ANY, '&About\tCTRL+A')
            self.help_menu.Bind(wx.EVT_MENU, self._openAboutDialog, self.help_about)
            self.menubar.Append(self.help_menu, 'Help')

        # View menu is platform independent
        self.view_menu = wx.Menu()

        self._createShowColMenuItems()

        self.view_menu.AppendSeparator()

        # Higlighting submenu for view menu
        self.hl_sub = wx.Menu()
        self.view_menu.Append(wx.ID_ANY, "Highlighting", self.hl_sub)

        self.hl_blops = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&Blops Use")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_blops)
        self.hl_blops.Check(self.options.Get("HlBlops", True))

        self.hl_cyno = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&Cyno Use")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_cyno)
        self.hl_cyno.Check(self.options.Get("HlCyno", True))

        self.hl_super = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&Super Use")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_super)
        self.hl_super.Check(self.options.Get("HlSuper", True))

        self.hl_titan = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&Titan Use")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_titan)
        self.hl_titan.Check(self.options.Get("HlTitan", True))

        self.hl_list = self.hl_sub.AppendCheckItem(wx.ID_ANY, "&Highlighted Entities List")
        self.hl_sub.Bind(wx.EVT_MENU, self._toggleHighlighting, self.hl_list)
        self.hl_list.Check(self.options.Get("HlList", True))

        # Toggle Stay on-top
        self.stay_ontop = self.view_menu.AppendCheckItem(wx.ID_ANY, 'Stay on-&top\tCTRL+T')
        self.view_menu.Bind(wx.EVT_MENU, self._toggleStayOnTop, self.stay_ontop)
        self.stay_ontop.Check(self.options.Get("StayOnTop", True))

        # Options Menubar
        self.opt_menu = wx.Menu()

        self.review_ignore = self.opt_menu.Append(wx.ID_ANY, "&Clear Ignored Entities\tCTRL+R")
        self.opt_menu.Bind(wx.EVT_MENU, self._clearIgnoredEntities, self.review_ignore)

        self.review_highlight = self.opt_menu.Append(wx.ID_ANY, "&Clear Highlighted Entities\tCTRL+H")
        self.opt_menu.Bind(wx.EVT_MENU, self._clearHighlightedEntities, self.review_highlight)

        self.opt_menu.AppendSeparator()

        self.clear_cache = self.opt_menu.Append(wx.ID_ANY, '&Clear Character Cache')
        self.opt_menu.Bind(wx.EVT_MENU, self._clear_character_cache, self.clear_cache)

        self.clear_kills = self.opt_menu.Append(wx.ID_ANY, "&Clear Killmail Cache")
        self.opt_menu.Bind(wx.EVT_MENU, self._clear_kill_cache, self.clear_kills)

        self.menubar.Append(self.opt_menu, 'Options')

        # Toggle Dark-Mode
        self.dark_mode = self.view_menu.AppendCheckItem(wx.ID_ANY, '&Dark Mode\tCTRL+D')
        self.dark_mode.Check(self.options.Get("DarkMode", True))
        self.view_menu.Bind(wx.EVT_MENU, self._toggleDarkMode, self.dark_mode)
        self.use_dm = self.dark_mode.IsChecked()

        self.menubar.Append(self.view_menu, 'View ')  # Added space to avoid autogenerated menu items on Mac

        # Set the grid object
        self.grid = wx.grid.Grid(self, wx.ID_ANY)
        self.grid.CreateGrid(0, 0)
        self.grid.SetName("Output List")
        self.grid.ShowScrollbars(wx.SHOW_SB_NEVER, wx.SHOW_SB_NEVER)

        # The status label shows various info and error messages.
        self.status_label = wx.StaticText(self,
                                          wx.ID_ANY,
                                          "Please copy some EVE character names to clipboard...",
                                          style=wx.ALIGN_LEFT | wx.ST_ELLIPSIZE_END
                                          )
        self.status_label.SetName("Status_Bar")

        # First set default properties, then restore persistence if any
        self.__set_properties()

        # Set up Persistence Manager
        self._persistMgr = pm.PersistenceManager.Get()
        self._persistMgr.SetPersistenceFile(config.GUI_CFG_FILE)
        self._persistMgr.RegisterAndRestoreAll(self)

        # Column resize to trigger last column stretch to fill blank canvas.
        self.Bind(wx.grid.EVT_GRID_COL_SIZE, self._stretchLastCol, self.grid)

        # Window resize to trigger last column stretch to fill blank canvas.
        self.Bind(wx.EVT_SIZE, self._stretchLastCol, self)

        # Ensure that Persistence Manager saves window location on close
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Bind double click on list item to zKill link.
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self._goToZKill, self.grid)

        # Bind right click on list item to ignore character.
        self.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self._showContextMenu, self.grid)

        # Bind left click on column label to sorting
        self.Bind(wx.grid.EVT_GRID_COL_SORT, self.sortOutlist, self.grid)

        # Set transparency based off restored slider
        self.__do_layout()

    def __set_properties(self, dark_toggle=None):
        """
        Set the initial properties for the various widgets.
        :param dark_toggle: Boolean indicating if only the properties related to the colour scheme should be set
        """
        # Colour Scheme Dictionaries
        self.dark_dict = config.DARK_MODE
        self.normal_dict = config.NORMAL_MODE

        # Colour Scheme
        if not self.options.Get("DarkMode", True):
            self.bg_colour = self.normal_dict["BG"]
            self.txt_colour = self.normal_dict["TXT"]
            self.lne_colour = self.normal_dict["LNE"]
            self.lbl_colour = self.normal_dict["LBL"]
            self.hl1_colour = self.normal_dict["HL1"]
            self.hl2_colour = self.normal_dict["HL2"]
            self.hl3_colour = self.normal_dict["HL3"]
            self.hl4_colour = self.normal_dict["HL4"]
            self.hl5_colour = self.normal_dict["HL5"]
        else:
            self.bg_colour = self.dark_dict["BG"]
            self.txt_colour = self.dark_dict["TXT"]
            self.lne_colour = self.dark_dict["LNE"]
            self.lbl_colour = self.dark_dict["LBL"]
            self.hl1_colour = self.dark_dict["HL1"]
            self.hl2_colour = self.dark_dict["HL2"]
            self.hl3_colour = self.dark_dict["HL3"]
            self.hl4_colour = self.dark_dict["HL4"]
            self.hl5_colour = self.dark_dict["HL5"]

        # Set default colors
        self.SetBackgroundColour(self.bg_colour)
        self.SetForegroundColour(self.txt_colour)
        self.grid.SetDefaultCellBackgroundColour(self.bg_colour)
        self.grid.SetDefaultCellTextColour(self.txt_colour)
        self.grid.SetGridLineColour(self.lne_colour)
        self.grid.SetLabelBackgroundColour(self.bg_colour)
        self.grid.SetLabelTextColour(self.lbl_colour)
        self.status_label.SetForegroundColour(self.lbl_colour)

        # Do not reset window size etc. if only changing colour scheme.
        if dark_toggle:
            return

        self.SetTitle(config.GUI_TITLE)
        self.SetSize((720, 400))
        self.SetMenuBar(self.menubar)

        # Insert columns based on parameters provided in col_def
        # self.grid.CreateGrid(0, 0)
        if self.grid.GetNumberCols() < len(self.columns):
            self.grid.AppendCols(len(self.columns))
        self.grid.SetColLabelSize(self.grid.GetDefaultRowSize() + 2)
        self.grid.SetRowLabelSize(0)
        self.grid.EnableEditing(0)
        self.grid.DisableCellEditControl()
        self.grid.EnableDragRowSize(0)
        self.grid.EnableDragGridSize(0)
        self.grid.SetSelectionMode(wx.grid.Grid.SelectRows)
        self.grid.SetColLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_BOTTOM)
        self.grid.ClipHorzGridLines(False)
        # self.grid.ClipVertGridLines(False)
        # Disable visual highlighting of selected cell to look more like listctrl
        self.grid.SetCellHighlightPenWidth(0)
        colidx = 0
        for col in self.columns:
            self.grid.SetColLabelValue(col[0],  # Index
                                       col[1],  # Heading
                                       )
            # self.grid.SetColSize(colidx, col[3])
            colidx += 1

    def __do_layout(self):
        """
        Assigns the various widgets to sizers and calls a number of helper functions
        """
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_bottom = wx.BoxSizer(wx.HORIZONTAL)
        sizer_main.Add(self.grid, 1, wx.EXPAND, 0)
        sizer_bottom.Add(self.status_label, 1, wx.ALIGN_CENTER_VERTICAL, 0)
        static_line = wx.StaticLine(self, wx.ID_ANY, style=wx.LI_VERTICAL)
        sizer_bottom.Add(static_line, 0, wx.EXPAND, 0)
        sizer_main.Add(sizer_bottom)
        self.SetSizer(sizer_main)
        self.Layout()
        self._restoreColWidth()
        self._stretchLastCol()

    def _createShowColMenuItems(self):
        """
        Populates the View menu with show column toggle menu items for each column that is toggleable. It uses the
        information provided in self.columns
        """
        # For each column, create show / hide menu items, if hideable
        self.col_menu_items = [[] for i in self.columns]
        for col in self.columns:
            if not col[4]:  # Do not add menu item if column not hideable
                continue
            index = col[0]
            options_key = "Show" + col[1]
            menu_name = "Show " + col[6]
            self.col_menu_items[index] = self.view_menu.AppendCheckItem(wx.ID_ANY, menu_name)
            # Column show / hide, depending on user settings, if any
            checked = self.options.Get(options_key, self.columns[index][5])
            self.col_menu_items[index].Check(self.options.Get(options_key, checked))
            # Bind new menu item to toggleColumn method
            self.view_menu.Bind(wx.EVT_MENU,
                                lambda evt,
                                index=index: self._toggleColumn(index, evt),
                                self.col_menu_items[index]
                                )

    def _toggleColumn(self, index, event=None):
        """
        Depending on the respective menu item state, either reveals or hides a column. If it hides a column, it first
        stores the old column width in self.options to allow for subsequent restore
        :param index: Integer representing the index of the column which is to be shown or hidden.
        """
        try:
            checked = self.col_menu_items[index].IsChecked()
        except:
            checked = False
        col_name = self.columns[index][1]
        if checked:
            default_width = self.columns[index][3]
            col_width = self.options.Get(col_name, default_width)
            if col_width > 0:
                self.grid.SetColSize(index, col_width)
            else:
                self.grid.SetColSize(index, default_width)
        else:
            col_width = self.grid.GetColSize(index)
            # Only save column status if column is actually hideable
            if self.columns[index][4]:
                self.options.Set(col_name, col_width)
            self.grid.HideCol(index)
        self._stretchLastCol()

    def _stretchLastCol(self, event=None):
        """
        Makes sure the last column fills any blank space of the grid. For this reason, the last list item of
        self.columns should describe an empty column.
        """
        grid_width = self.grid.Size.GetWidth()
        cols_width = 0
        for index in range(self.columns[-1][0] + 1):
            cols_width += self.grid.GetColSize(index)
        stretch_width = grid_width - cols_width
        last_col_width = max(self.grid.GetColSize(index) + stretch_width, self.columns[index][3])
        self.grid.SetColSize(index, last_col_width)
        self.Layout()
        if event is not None:
            event.Skip(True)

    def updateList(self, outlist, duration=None, filtered=None):
        """
        updateList() takes the output of main() in analyze.py (via sortOutlist()) or a copy thereof stored in
        self.option, and uses it to populate the grid widget. Before it does so, it checks each item in outlist against
        a list of ignored characters, corporations and alliances. Finally, it highlights certain characters and updates
        the statusbar message.
        :param outlist: A list of dictionaries with character data
        :param duration: Time in seconds taken to query all relevant databases for each character
        :param filtered: How many characters were not run (filtered)
        """
        # If updateList() gets called before outlist has been provided, do nothing
        if outlist is None:
            return
        highlighted_list = self.options.Get("highlightedList", default=[])
        # Clean up grid
        if self.grid.GetNumberRows() > 0:
            self.grid.DeleteRows(numRows=self.grid.GetNumberRows())
        self.grid.AppendRows(len(outlist))
        # Add any NPSI fleet related characters to ignored_list
        ignored_list = self.options.Get("ignoredList", default=[])
        ignore_count = 0
        rowidx = 0
        for r in outlist:
            ignore = False
            for rec in ignored_list:
                if r['id'] == rec[0] or r['corp_id'] == rec[0] or r['alliance_id'] == rec[0]:
                    ignore = True
            if ignore:
                self.grid.HideRow(rowidx)
                ignore_count += 1

            # Schema depending on output_list() in analyze.py
            out = [
                r['pilot_id'],
                r['warning'],
                r['pilot_name'],
                r['corp_name'],
                r['alliance_name'],
                '{:.0%}'.format(r['cyno']),
                '{} ({:.0%})'.format(r['avg_gang'], r['pro_gang'] / (r['processed_killmails'] + 0.01)),
                '{} ({:.0%})'.format(r['avg_10'], r['pro_10'] / (r['processed_killmails'] + 0.01)),
                r['timezone'],
                r['top_ships'],
                r['top_gang_ships'],
                r['top_10_ships'],
                '{} ({:.0%})'.format(r['boy_scout'], r['boy_scout'] / (r['processed_killmails'] + 0.01)),
                r['super'],
                r['titan'],
                '{:.0%}'.format(r['capital_use']),
                '{:.0%}'.format(r['blops_use']),
                r['top_regions']
                ]
            colidx = 0

            # Cell text formatting
            for value in out:
                color = False
                self.grid.SetCellValue(rowidx, colidx, str(value))
                self.grid.SetCellAlignment(self.columns[colidx][2], rowidx, colidx, 0)
                if self.options.Get("HlBlops", True) and r['blops_use'] > config.BLOPS_HL_PERCENTAGE:
                    self.grid.SetCellTextColour(rowidx, colidx, self.hl1_colour)
                    color = True
                if self.options.Get("HlCyno", True) and r['cyno'] > config.CYNO_HL_PERCENTAGE:
                    self.grid.SetCellTextColour(rowidx, colidx, self.hl2_colour)
                    color = True

                if self.options.Get("HlSuper", True) and r['super'] > 0:
                    self.grid.SetCellTextColour(rowidx, colidx, self.hl4_colour)
                    color = True

                if self.options.Get("HlTitan", True) and r['titan'] > 0:
                    self.grid.SetCellTextColour(rowidx, colidx, self.hl5_colour)
                    color = True

                for entry in highlighted_list:  # Highlight chars from highlight list
                    if self.options.Get("HlList", True) and (entry[0] == r['id'] or entry[0] == r['corp_id'] or entry[0] == r['alliance_id']):
                        self.grid.SetCellTextColour(rowidx, colidx, self.hl3_colour)
                        color = True

                if not color:
                    self.grid.SetCellTextColour(rowidx, colidx, self.txt_colour)
                colidx += 1
            rowidx += 1

        Logger.info("{} characters analysed, in {} seconds ({} filtered).".format(len(outlist), duration, filtered))
        statusmsg.push_status("{} characters analysed, in {} seconds ({} filtered). Double click character to go to "
                              "zKillboard.".format(len(outlist), duration, filtered))

    def updateStatusbar(self, msg):
        """
        Gets called by push_status() in statusmsg.py.
        :param msg: Message to be pushed to the statusbar
        """
        if isinstance(msg, str):
            self.status_label.SetLabel(msg)
            self.Layout()

    def _goToZKill(self, event):
        """
        Get the pilot_id from the row and open the relevant zkill page for given id
        :param event: Required
        """
        rowidx = event.GetRow()
        character_id = self.options.Get("outlist")[rowidx]['id']
        url = "https://zkillboard.com/character/{}/".format(str(character_id))

        webbrowser.open_new_tab(url)

    def _showContextMenu(self, event):
        """
        Gets invoked by right click on any list item and produces a context menu that allows the user to add the
        selected character/corp/alliance to HawkEye's list of "ignored characters" which will no longer be shown in
        search results, OR add the selected character/corp/alliance to HawkEye's list of "highlighted characters" which
        will hihglight them in the grid.
        :param event: Required
        """
        def OnIgnore(id, name, type, e=None):
            ignored_list = self.options.Get("ignoredList", default=[])
            ignored_list.append([id, name, type])
            self.options.Set("ignoredList", ignored_list)
            self.updateList(self.options.Get("outlist", None))

        def OnHighlight(id, name, type, e=None):
            highlighted_list = self.options.Get("highlightedList", default=[])
            if [id, name, type] not in highlighted_list:
                highlighted_list.append([id, name, type])
            self.options.Set("highlightedList", highlighted_list)
            self.updateList(self.options.Get("outlist", None))

        def OnDeHighlight(id, name, type, e=None):
            highlighted_list = self.options.Get("highlightedList", default=[])
            highlighted_list.remove([id, name, type])
            self.options.Set("highlightedList", highlighted_list)
            self.updateList(self.options.Get("outlist", None))

        highlighted_list = self.options.Get("highlightedList", default=[])
        rowidx = event.GetRow()
        character_id = str(self.options.Get("outlist")[rowidx]['id'])
        # Only open context menu character item right clicked, not empty line.
        if len(character_id) > 0:
            outlist = self.options.Get("outlist")
            for r in outlist:
                if str(r['pilot_id']) == character_id:
                    character_id = r['pilot_id']
                    character_name = r['pilot_name']
                    corp_id = r['corp_id']
                    corp_name = r['corp_name']
                    alliance_id = r['alliance_id']
                    alliance_name = r['alliance_name']
                    break
            self.menu = wx.Menu()
            # Context menu to ignore characters, corporations and alliances.
            item_ig_char = self.menu.Append(wx.ID_ANY, "Ignore character '" + character_name + "'")
            self.menu.Bind(wx.EVT_MENU,
                           lambda evt,
                           id=character_id,
                           name=character_name: OnIgnore(id, name, "Character", evt),
                           item_ig_char
                           )

            item_ig_corp = self.menu.Append(wx.ID_ANY, "Ignore corporation: '" + corp_name + "'")
            self.menu.Bind(wx.EVT_MENU,
                           lambda evt,
                           id=corp_id,
                           name=corp_name: OnIgnore(id, name, "Corporation", evt),
                           item_ig_corp
                           )

            if alliance_name != 'None':
                item_ig_alliance = self.menu.Append(wx.ID_ANY, "Ignore alliance: '" + alliance_name + "'")
                self.menu.Bind(wx.EVT_MENU,
                               lambda evt,
                               id=alliance_id,
                               name=alliance_name: OnIgnore(id, name, "Alliance", evt),
                               item_ig_alliance
                               )

            self.menu.AppendSeparator()

            hl_char = False
            hl_corp = False
            hl_alliance = False

            for entry in highlighted_list:
                if entry[0] == self.options.Get("outlist")[rowidx]['id']:
                    hl_char = True
                if entry[0] == self.options.Get("outlist")[rowidx]['corp_id']:
                    hl_corp = True
                if alliance_name != 'None':
                    if entry[0] == self.options.Get("outlist")[rowidx]['alliance_id']:
                        hl_alliance = True

            # Context menu to highlight characters, corporations and alliances
            if not hl_char:
                item_hl_char = self.menu.Append(wx.ID_ANY, "Highlight character '" + character_name + "'")
                self.menu.Bind(
                    wx.EVT_MENU,
                    lambda evt, id=character_id, name=character_name: OnHighlight(id, name, "Character", evt),
                    item_hl_char
                )
            else:
                item_hl_char = self.menu.Append(wx.ID_ANY, "Stop highlighting character '" + character_name + "'")
                self.menu.Bind(
                    wx.EVT_MENU,
                    lambda evt, id=character_id, name=character_name: OnDeHighlight(id, name, "Character", evt),
                    item_hl_char
                )

            if not hl_corp:
                item_hl_corp = self.menu.Append(wx.ID_ANY, "Highlight corporation '" + corp_name + "'")
                self.menu.Bind(
                    wx.EVT_MENU,
                    lambda evt, id=corp_id, name=corp_name: OnHighlight(id, name, "Corporation", evt),
                    item_hl_corp
                )
            else:
                item_hl_corp = self.menu.Append(wx.ID_ANY, "Stop highlighting corporation '" + corp_name + "'")
                self.menu.Bind(
                    wx.EVT_MENU,
                    lambda evt, id=corp_id, name=corp_name: OnDeHighlight(id, name, "Corporation", evt),
                    item_hl_corp
                )

            if alliance_name != 'None':
                if not hl_alliance:
                    item_hl_alliance = self.menu.Append(wx.ID_ANY, "Highlight alliance: '" + alliance_name + "'")
                    self.menu.Bind(
                        wx.EVT_MENU,
                        lambda evt, id=alliance_id, name=alliance_name: OnHighlight(id, name, "Alliance", evt),
                        item_hl_alliance
                    )
                else:
                    item_hl_alliance = self.menu.Append(wx.ID_ANY,
                                                        "Stop highlighting alliance: '" + alliance_name + "'"
                                                        )
                    self.menu.Bind(
                        wx.EVT_MENU,
                        lambda evt, id=alliance_id, name=alliance_name: OnDeHighlight(id, name, "Alliance", evt),
                        item_hl_alliance
                    )

            self.PopupMenu(self.menu, event.GetPosition())
            self.menu.Destroy()

    def sortOutlist(self, event=None, outlist=None, duration=None, filtered=None):
        """
        Pass the outlist to sortarray.sort_array() and pass back to updateList to refresh gui view.
        :param event: Required
        :param outlist: outlist to process
        :param duration: How long outlist took to generate (typically given when called by __main__)
        :param filtered: How many pilots were filtered out before processing the clipboard (typically given when called
        by __main__)
        """
        if event is None:
            # Default sort by character name ascending.
            colidx = self.options.Get("SortColumn", self.columns[3][0])
            sort_desc = self.options.Get("SortDesc", False)
        else:
            colidx = event.GetCol()
            if self.options.Get("SortColumn", -1) == colidx:
                sort_desc = not self.options.Get("SortDesc")
            else:
                sort_desc = True

        # Use unicode characters for sort indicators
        arrow = u"\u2193" if sort_desc else u"\u2191"

        # Reset all labels
        for col in self.columns:
            self.grid.SetColLabelValue(col[0], col[1])

        # Assign sort indicator to sort column
        self.grid.SetColLabelValue(colidx, self.columns[colidx][1] + " " + arrow)
        self.options.Set("SortColumn", colidx)
        self.options.Set("SortDesc", sort_desc)
        event = None
        # Sort outlist. Note: outlist columns are not the same as self.grid columns!!!
        if outlist is None:
            outlist = self.options.Get("outlist", False)

        if outlist:
            outlist = sortarray.sort_array(
                outlist,
                self.columns[colidx][7],
                sec_col='pilot_name',  # Secondary sort by name
                prim_desc=sort_desc,
                sec_desc=False,  # Secondary sort by name always ascending
                case_sensitive=False
                )
        self.options.Set("outlist", outlist)
        self.updateList(outlist, duration=duration, filtered=filtered)

    def _toggleHighlighting(self, e):
        """
        Check and set highlight options, pass to updateList to refresh grid view
        :param e: Required
        """
        self.options.Set("HlBlops", self.hl_blops.IsChecked())
        self.options.Set("HlCyno", self.hl_cyno.IsChecked())
        self.options.Set("HlList", self.hl_list.IsChecked())
        self.options.Set("HlSuper", self.hl_super.IsChecked())
        self.options.Set("HlTitan", self.hl_titan.IsChecked())
        self.updateList(self.options.Get("outlist", None))

    def _toggleStayOnTop(self, evt=None):
        """
        Check and set stay on top option, then set that option for entire Frame
        :param evt: Required
        """
        self.options.Set("StayOnTop", self.stay_ontop.IsChecked())
        self.ToggleWindowStyle(wx.STAY_ON_TOP)

    def _toggleDarkMode(self, evt=None):
        """
        Check and set dark mode, then call __set_properties to change settings, then refresh the GUI, then finally
        refresh the grid
        :param evt: Required
        """
        self.options.Set("DarkMode", self.dark_mode.IsChecked())
        self.use_dm = self.dark_mode.IsChecked()
        self.__set_properties(dark_toggle=True)
        self.Refresh()
        self.Update()
        self.updateList(self.options.Get("outlist"))

    def _openAboutDialog(self, evt=None):
        """
        Checks if AboutDialog is already open. If not, opens the dialog window, otherwise brings the existing dialog
        window to the front.
        :param evt: Required
        """
        for c in self.GetChildren():
            if c.GetName() == "AboutDialog":  # Needs to match name in aboutdialog.py
                c.Raise()
                return
        aboutdialog.showAboutBox(self)

    def _clearIgnoredEntities(self, evt=None):
        """
        Empty the options ignoreList
        :param evt: Required
        """
        self.options.Set("ignoredList", [])
        self.updateList(self.options.Get("outlist", None))
        statusmsg.push_status("Cleared ignored entities")

    def _clearHighlightedEntities(self, evt=None):
        """
        Empty the options highlightedList
        :param evt: Required
        """
        self.options.Set("highlightedList", [])
        self.updateList(self.options.Get("outlist", None))
        statusmsg.push_status("Cleared highlighted entities")

    def _restoreColWidth(self):
        """
        Restores column width either to default or value stored from previous session
        """
        for col in self.columns:
            header = col[1]
            # Column width is also set in _toggleColumn()
            width = self.options.Get(header, col[3])
            menu_item = self.col_menu_items[col[0]]
            if menu_item == [] or menu_item.IsChecked():
                self.grid.SetColSize(col[0], width)
            else:
                self.grid.SetColSize(col[0], 0)
            pass

    def _saveColumns(self):
        """
        Saves custom column widths, since wxpython's Persistence Manager is unable to do so for Grid widgets
        """
        for col in self.columns:
            is_hideable = col[4]
            default_show = col[5]
            header = col[1]
            options_key = "Show" + header
            width = self.grid.GetColSize(col[0])
            try:
                menu_item_chk = self.col_menu_items[col[0]].IsChecked()
            except:
                menu_item_chk = False
            # Only save column width for columns that are not hidden or
            # not hideable and shown by default.
            if menu_item_chk or (not is_hideable and default_show):
                self.options.Set(header, width)
            # Do not add menu item if column not hideable
            if col[4]:
                self.options.Set(options_key, menu_item_chk)
            pass

    def _clear_character_cache(self, e):
        """
        Call eveDB.clear_characters() which empties the characters.db
        """
        eveDB.clear_characters()
        statusmsg.push_status("Cleared character cache")

    def _clear_kill_cache(self, e):
        """
        Use shutil.rmtree() to remove the entire kills folder and stored kills
        :param e:
        """
        if os.path.exists(os.path.join(config.PREF_PATH, 'kills/')):
            shutil.rmtree(os.path.join(config.PREF_PATH, 'kills/'))

    def OnClose(self, event=None):
        """
        Run a few clean-up tasks on close and save persistent properties
        """
        self._persistMgr.SaveAndUnregister()

        # Save column toggle menu state and column width in pickle container
        self._saveColumns()

        # Store check-box values in pickle container
        self.options.Set("StayOnTop", self.stay_ontop.IsChecked())
        self.options.Set("DarkMode", self.dark_mode.IsChecked())
        # Delete last outlist and NPSIList
        self.options.Set("outlist", None)
        # Write pickle container to disk
        self.options.Save()
        event.Skip() if event else False

    def OnQuit(self, e):
        """
        Quit
        :param e: Required
        """
        self.Close()


class App(wx.App):
    """
    General App class
    """
    def OnInit(self):
        self.MyFrame = Frame(None, wx.ID_ANY, "")
        self.SetTopWindow(self.MyFrame)
        self.MyFrame.Show()
        return True
