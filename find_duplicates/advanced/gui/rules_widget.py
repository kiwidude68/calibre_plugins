#!/usr/bin/env python
# ~*~ coding: utf-8 ~*~

__license__ = 'GPL v3'
__copyright__ = '2020, Ahmed Zaki <azaki00.dev@gmail.com>'

from functools import partial
import copy

# Maintain backwards compatibility with older versions of Qt and calibre.
try:
    from qt.core import (Qt, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout,
                        QLabel, QGroupBox, QToolButton, QPushButton, QScrollArea, QComboBox,
                        QDialogButtonBox, QCheckBox, QIcon, pyqtSignal, 
                        QSpacerItem, QModelIndex)
except ImportError:
    from PyQt5.Qt import (Qt, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout,
                        QLabel, QGroupBox, QToolButton, QPushButton, QScrollArea, QComboBox,
                        QDialogButtonBox, QCheckBox, QIcon, pyqtSignal, 
                        QSpacerItem, QModelIndex)

from calibre.gui2 import error_dialog, gprefs

from calibre_plugins.find_duplicates.common_compatibility import (qSizePolicy_Expanding, qSizePolicy_Minimum,
                                                                qSizePolicy_Maximum, qSizePolicy_Preferred)
from calibre_plugins.find_duplicates.common_icons import get_icon
from calibre_plugins.find_duplicates.common_dialogs import SizePersistedDialog
from calibre_plugins.find_duplicates.advanced.common import truncate, get_cols, column_metadata
from calibre_plugins.find_duplicates.advanced.gui.sort import SortDialog, check_sort_filter
from calibre_plugins.find_duplicates.advanced.match_rules import check_match_rule, parse_match_rule_errors
from calibre_plugins.find_duplicates.advanced.gui.views import AlgorithmsTable
from calibre_plugins.find_duplicates.advanced.gui.models import AlgorithmsModel, UP, DOWN
import calibre_plugins.find_duplicates.config as cfg

try:
    load_translations()
except NameError:
    pass

class AlgorithmsDialog(SizePersistedDialog):
    def __init__(self, parent, gui, algorithms_config, algorithms):
        self.algorithms = algorithms
        self.gui = gui
        self.db = self.gui.current_db
        self.algorithms_config = copy.deepcopy(algorithms_config)
        SizePersistedDialog.__init__(self, parent, 'find-duplicates-algorithms-dialog')
        self.setup_ui()
        self.setWindowTitle('Algorithms Dialog')
        self.resize_dialog()

    def setup_ui(self):
        self.setWindowTitle(_('Add algorithms'))
        l = QVBoxLayout()
        self.setLayout(l)

        settings_l = QGridLayout()
        l.addLayout(settings_l)

        table_groupbox = QGroupBox(_('Algorithms'))
        table_layout = QHBoxLayout()
        table_groupbox.setLayout(table_layout)
        l.addWidget(table_groupbox)
        
        self._table = AlgorithmsTable(self, self.gui, self.algorithms)
        table_layout.addWidget(self._table)
        
        algorithms_model = AlgorithmsModel(self.algorithms, self.algorithms_config)
        algorithms_model.validate()
        self._table.set_model(algorithms_model)
        self._table.selectionModel().selectionChanged.connect(self._on_table_selection_change)
        
        # Restore table state
        state = gprefs.get(cfg.KEY_ALGORITHMS_TABLE_STATE)
        if state:
            self._table.apply_state(state)

        # Add a vertical layout containing the the buttons to move up/down etc.
        button_layout = QVBoxLayout()
        table_layout.addLayout(button_layout)
        
        move_up_button = self.move_up_button = QToolButton(self)
        move_up_button.setToolTip(_('Move row up'))
        move_up_button.setIcon(QIcon(I('arrow-up.png')))
        button_layout.addWidget(move_up_button)
        spacerItem1 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem1)

        add_button = self.add_button = QToolButton(self)
        add_button.setToolTip(_('Add row'))
        add_button.setIcon(QIcon(I('plus.png')))
        button_layout.addWidget(add_button)
        spacerItem2 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem2)

        copy_button = self.copy_button = QToolButton(self)
        copy_button.setToolTip(_('Duplicate algorithm'))
        copy_button.setIcon(QIcon(I('edit-copy.png')))
        button_layout.addWidget(copy_button)
        spacerItem3 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem3)

        delete_button = self.delete_button = QToolButton(self)
        delete_button.setToolTip(_('Delete row'))
        delete_button.setIcon(QIcon(I('minus.png')))
        button_layout.addWidget(delete_button)
        spacerItem4 = QSpacerItem(20, 40, qSizePolicy_Minimum, qSizePolicy_Expanding)
        button_layout.addItem(spacerItem4)

        move_down_button = self.move_down_button = QToolButton(self)
        move_down_button.setToolTip(_('Move row down'))
        move_down_button.setIcon(QIcon(I('arrow-down.png')))
        button_layout.addWidget(move_down_button)

        move_up_button.clicked.connect(partial(self._table.move_rows,UP))
        move_down_button.clicked.connect(partial(self._table.move_rows,DOWN))
        add_button.clicked.connect(self._table.add_row)
        delete_button.clicked.connect(self._table.delete_rows)
        copy_button.clicked.connect(self._table.copy_row)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        l.addWidget(self.button_box)
        
        self._on_table_selection_change()

    def _on_table_selection_change(self):
        sm = self._table.selectionModel()
        selection_count = len(sm.selectedRows())
        self.delete_button.setEnabled(selection_count > 0)
        self.copy_button.setEnabled(selection_count == 1)
        self.move_up_button.setEnabled(selection_count > 0)
        self.move_down_button.setEnabled(selection_count > 0)

    def save_table_state(self):
        # Save table state
        gprefs[cfg.KEY_ALGORITHMS_TABLE_STATE] = self._table.get_state()

    def reject(self):
        self.save_table_state()
        SizePersistedDialog.reject(self)

    def accept(self):
        self.save_table_state()
        
        if self._table.model().rowCount(QModelIndex()) < 1:
            return error_dialog(
                self,
                _('No algorithms selected'),
                _('You must select at least one algorithm.'),
                show=True
            )
        is_valid = self._table.model().validate()
        if is_valid is not True:
            msg, details = _('Invalid algorithms'), _('Some algorithms are not valid. Double click on error cell for more details.')
            return error_dialog(
                self,
                msg,
                details,
                show=True
            )

        algorithms_config = self._table.model().algorithms_config
        # Remove error keys from algorithms_config
        for algorithm_config in algorithms_config:
            try:
                del algorithm_config['errors']
            except:
                pass
        self.algorithms_config = algorithms_config
        SizePersistedDialog.accept(self)

class MatchRuleControl(QGroupBox):
    
    match_rule_updated = pyqtSignal(bool)
    
    def __init__(self, parent, gui, algorithms, chosen_algos=[], mode='duplicates'):
        self.algorithms = algorithms
        self.possible_cols = parent.possible_cols
        self.mode = mode
        self.chosen_algos = chosen_algos
        self.rules_widget = parent
        self.parent_dialog = self.rules_widget.parent_dialog
        self.gui = gui
        self.db = self.gui.current_db
        self._init_controls()

    def _init_controls(self):
        QGroupBox.__init__(self)
        
        l = QGridLayout()
        self.setLayout(l)

        row_idx = 0
        if not self.mode == 'metadata_variations':
            remove_label = QLabel('<a href="close">✕</a>')
            remove_label.setToolTip(_('Remove'))
            remove_label.linkActivated.connect(self._remove)
            l.addWidget(remove_label, row_idx, 1, 1, 1, Qt.AlignRight)
            row_idx += 1

        gb1 = QGroupBox(_('Column:'))
        gb1_l = QHBoxLayout()
        gb1.setLayout(gb1_l)
        self.col_combo_box = QComboBox()
        self.col_combo_box.addItems(self.possible_cols)
        self.col_combo_box.setCurrentIndex(-1)
        self.col_combo_box.currentTextChanged.connect(self._field_changed)
        gb1_l.addWidget(self.col_combo_box)
        l.addWidget(gb1, row_idx, 0, 1, 1)

        gb2 = QGroupBox(_('Algorithms:'))
        gb2_l = QHBoxLayout()
        gb2.setLayout(gb2_l)

        self.algos_label = QLabel(_('0 Algorithms Chosen'))
        algos_button = QToolButton()
        algos_button.setIcon(get_icon('gear.png'))
        algos_button.setToolTip(_('Add or remove algorithms'))
        algos_button.clicked.connect(self._add_remove_algos)
        gb2_l.addWidget(self.algos_label)
        gb2_l.addWidget(algos_button)
        l.addWidget(gb2, row_idx, 1, 1, 1)
        row_idx += 1

        if not self.mode == 'metadata_variations':
            self.multiply_check = QCheckBox(_('Match any of the items'))
            self.multiply_check.setToolTip(_(
                'For fields with multiple items, match with books that any one of the items in this field.\n'
                'if unchecked, books match only when they match on all the items in the field.'
            ))
            self.names_check = QCheckBox(_('contains names').format(self.col_combo_box.currentText()))
            self.names_check.setToolTip(_(
                'Check if composite column contains names'
            ))            
            self.multiply_check.hide()
            self.names_check.hide()
            l.addWidget(self.multiply_check, row_idx, 0, 1, 1)
            l.addWidget(self.names_check, row_idx, 1, 1, 1)
            row_idx += 1
        
        self.setSizePolicy(qSizePolicy_Preferred, qSizePolicy_Maximum)

    def apply_match_rule(self, match_rule):
        chosen_algos = match_rule.get('algos', [])
        if len(chosen_algos) > 0:
            self.update_chosen_algos(chosen_algos)
        field = match_rule.get('field')
        multiply = match_rule.get('multiply', True)
        has_names = match_rule.get('composite_has_names', False)
        if field:
            idx = self.col_combo_box.findText(field)
            if idx != -1:
                self.col_combo_box.setCurrentIndex(idx)
                self._field_changed(self.col_combo_box.currentText())
            if not self.mode == 'metadata_variations':
                self.multiply_check.setChecked(multiply)
                self.names_check.setChecked(has_names)
        self.match_rule_updated.emit(self.isComplete()) 

    def _remove(self):
        if self.rules_widget.controls_layout.count() == 1:
            error_dialog(
                self,
                _('Cannot delete rule'),
                _('You must have at least one matching rule to proceed'),
                show=True
            )
            return
        rules_widget = self.rules_widget
        self.setParent(None)
        self.deleteLater()
        
        rules_widget.match_rules_updated.emit(rules_widget.isComplete() and not rules_widget.controls_layout.count() == 0)

    def update_chosen_algos(self, chosen_algos):
        self.chosen_algos = chosen_algos
        algos_no = len(self.chosen_algos)
        try:
            first_algo_name = self.chosen_algos[0]['name']
        except:
            first_algo_name = ''
        if algos_no == 0:
            text = _('0 Algorithms Chosen')
        elif algos_no == 1:
            text = '{}'.format(truncate(first_algo_name, length=30))
        else:
            text = _('{} + {} others').format(truncate(first_algo_name), algos_no-1)
        self.algos_label.setText(text)
        
        self.match_rule_updated.emit(self.isComplete())

    def _add_remove_algos(self):
        d = AlgorithmsDialog(self.parent_dialog, self.gui, self.chosen_algos, self.algorithms)
        if d.exec_() == d.Accepted:
            self.update_chosen_algos(chosen_algos=d.algorithms_config)

    def _field_changed(self, field):
        if not self.mode == 'metadata_variations':
            multiply_status = column_metadata(self.db, field)['is_multiple'] != {}
            self.multiply_check.setEnabled(multiply_status)
            self.multiply_check.setChecked(multiply_status)
            if multiply_status:
                self.multiply_check.show()
            else:
                self.multiply_check.hide()
            
            name_status = multiply_status and ( column_metadata(self.db, field)['datatype'] == 'composite' )
            self.names_check.setChecked(False)
            self.names_check.setEnabled(name_status)
            if name_status:
                self.names_check.show()
            else:
                self.names_check.hide()

        self.match_rule_updated.emit(self.isComplete())

    def isComplete(self):
        '''returns True only if a field and algorithm are chosen'''
        if self.col_combo_box.currentText() == '':
            return False
        if not self.chosen_algos:
            return False
        return True
    
    def get_match_rule(self):
        res = {}
        res['field'] = self.col_combo_box.currentText()
        if not self.mode == 'metadata_variations':
            res['multiply'] = self.multiply_check.isChecked()
            res['composite_has_names'] = self.names_check.isChecked()
        res['algos'] = self.chosen_algos
        return res

class RulesWidget(QWidget):

    match_rules_updated = pyqtSignal(bool)
    
    def __init__(self, parent_dialog, gui, algorithms, possible_cols=[], mode='duplicates', has_sort=False, target_db=None):
        self.mode = mode
        self.algorithms = algorithms
        self.parent_dialog = parent_dialog
        self.gui = gui
        self.db = self.gui.current_db
        self.target_db = target_db
        self.possible_cols = possible_cols
        if not self.possible_cols:
            self.possible_cols = self.get_possible_cols()
        self.has_sort = has_sort
        self.sort_filters = {}
        self._init_controls()

    def get_possible_cols(self):
        all_cols = get_cols(self.db)
        if self.mode == 'metadata_variations':
            possible_cols = []
            for column in all_cols:
                datatype = column_metadata(self.db, column)['datatype']
                if datatype in ['text','series']:
                    if column not in ['title','languages','formats']:
                        possible_cols.append(column)
            return possible_cols
        else:
            return all_cols

    def _init_controls(self):
        QWidget.__init__(self)
        l = QVBoxLayout()
        self.setLayout(l)
        
        if not self.mode == 'metadata_variations':
            hl1 = QHBoxLayout()
            clear_button = QPushButton(_('Clear'))
            clear_button.setToolTip(_('Clear all match rules'))
            clear_button.setIcon(get_icon('clear_left.png'))
            clear_button.clicked.connect(self.reset)
            clear_button.clicked.connect(self.match_rules_updated)
            hl1.addWidget(clear_button)
            hl1.addStretch(1)

            if self.has_sort:
                sort_button = QPushButton(_('Duplicates sort'), self)
                sort_button.setIcon(QIcon(I('sort.png')))
                sort_button.setToolTip(_('Configure sort filters for books inside duplicate groups'))
                sort_button.clicked.connect(self._sort_button_clicked)
                hl1.addWidget(sort_button)
                hl1.addStretch(1)

            add_button = QPushButton(_('Add Match Rules'))
            add_button.setToolTip(_('Add a rule containing a field and one or more match algorithm/template(s).'))
            add_button.setIcon(get_icon('plus.png'))
            add_button.clicked.connect(self.add_control)
            hl1.addWidget(add_button)
            l.addLayout(hl1)

        w = QWidget(self)
        self.controls_layout = QVBoxLayout()
        self.controls_layout.setSizeConstraint(self.controls_layout.SetMinAndMaxSize)
        w.setLayout(self.controls_layout)
        
        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(qSizePolicy_Minimum, qSizePolicy_Preferred)
        scroll.setObjectName('myscrollarea')
        scroll.setStyleSheet('#myscrollarea {background-color: transparent}')
        scroll.setWidget(w)
         
        l.addWidget(scroll)
        
        self._add_control(match_rule={})

    def isComplete(self):
        '''return True if all controls have fields and algorithms set'''
        for idx in range(self.controls_layout.count()):
            control = self.controls_layout.itemAt(idx).widget()
            if not control.isComplete():
                return False
        return True

    def _add_control(self, match_rule={}):
        control = MatchRuleControl(self, self.gui, self.algorithms, mode=self.mode)
        control.match_rule_updated.connect(self.match_rules_updated)
        if match_rule:
            control.apply_match_rule(match_rule)
        self.controls_layout.addWidget(control)
        control.match_rule_updated.emit(control.isComplete())
        if self.mode == 'metadata_variations':
            self.control = control

    def add_control(self):
        if not self.isComplete():
            error_dialog(
                self,
                _('Incomplete Match Rule'),
                _('You must complete the previous match rule(s) before adding any new rules.'),
                show=True
            )
            return
        self._add_control(match_rule={})

    def reset(self, possible_cols=[], add_empty_control=True):
        if possible_cols:
            self.possible_cols = possible_cols
        # remove controls in reverse order
        for idx in reversed(range(self.controls_layout.count())):
            control = self.controls_layout.itemAt(idx).widget()
            control.setParent(None)
            control.deleteLater()
        if add_empty_control:
            self._add_control(match_rule={})
        self.sort_filters = {}
        self.match_rules_updated.emit(self.isComplete() and not self.controls_layout.count() == 0)

    def get_match_rules(self):
        match_rules = []
        for idx in range(self.controls_layout.count()):
            control = self.controls_layout.itemAt(idx).widget()
            match_rules.append(control.get_match_rule())
        return match_rules

    def get_rules_and_filters(self):
        match_rules = self.get_match_rules()
        return {
            'match_rules': match_rules,
            'sort_filters': self.sort_filters
        }

    def restore_match_rules(self, match_rules, add_to_existing=False):

        error_msg = ''

        if len(match_rules) > 1 and ( self.mode == 'metadata_variations'):
            msg = _('Saved setting contains more than one match rule. Metadata variations can only have one match rule')
            return msg

        if self.mode == 'metadata_variations':
            add_to_existing=False
        
        if not add_to_existing:
            self.reset(self.possible_cols, add_empty_control=False)

        for idx, match_rule in enumerate(match_rules, 1):
            new_match_rule, has_errors, errors = check_match_rule(self.gui, self.algorithms, match_rule, self.possible_cols, self.target_db)
            self._add_control(new_match_rule)
            if has_errors:
                msg = parse_match_rule_errors(errors, idx)        
                error_msg += msg + '\n'

        if error_msg:
            return error_msg
        else:
            return True

    def restore_rules_and_filters(self, rules_and_filters, add_to_existing=False, show_error_msg=True):
        match_rules = rules_and_filters['match_rules']
        sort_filters = rules_and_filters.get('sort_filters', [])
        
        error_msg = ''
        
        res = self.restore_match_rules(match_rules, add_to_existing=add_to_existing)
        if res is not True:
            error_msg += res

        if self.has_sort:
            new_sort_filters = []
            for idx, sort_filter in enumerate(sort_filters, 1):
                has_errors = check_sort_filter(sort_filter, self.possible_cols, self.gui)
                
                if has_errors:
                    error_msg += '\n' + _('Error in sort filter No. {}: {}').format(idx, sort_filter) + '\n'
                else:
                    new_sort_filters.append(sort_filter)
            self.sort_filters = new_sort_filters

        if error_msg:
            if show_error_msg:
                error_dialog(
                self,
                _('Restore Error'),
                _('Encountered errors while restoring settings'),
                det_msg=error_msg,
                show=True
                )
            return False
        else:
            return True

    def _sort_button_clicked(self):
        d = SortDialog(self.gui, self.sort_filters)
        if d.exec_() == d.Accepted:
            self.sort_filters = d.sort_filters
