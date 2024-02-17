import sys
import os
import re
from typing import Tuple, Dict
import _sqlite3 as sql
from PyQt6 import uic
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QWidget, \
    QMessageBox, QStyledItemDelegate, QCheckBox, QFileDialog
from PyQt6.QtSql import *
from PyQt6.QtCore import Qt, QDate
import numpy as np
import pandas as pd
import datetime
from datetime import datetime
from datetime import timedelta
from sqlite3 import connect
from scipy.stats import kstest
import matplotlib.pyplot as plt

LOGICAL_OPERATORS = [
    '>=', '<=', '=', '>', '<'
]

COLUMNS_DICT = {
    'Код_серии': 'Код серии',
    'Дата_торгов': "Дата торгов",
    'Дата_исполнения': 'Дата исполнения',
    'Дата_погашения': 'Дата погашения',
    'Число_продаж': 'Число продаж',
    'Текущая_цена': 'Текущая цена\nв процентах %',
    'Минимальная_цена': 'Минимальная цена\nв процентах %',
    'Максимальная_цена': 'Максимальная цена\nв процентах %',
    'Код_фьючерса': 'Код фьючерса',
    'index': 'index',
    'rk': 'rk',
    'xk': 'xk',
    'min': 'Минимум',
    'max': 'Максимум',
    'mean': 'Среднее',
    'Дата_начала_торгов': 'Дата начала\nторгов',
    'len': 'Длина предыстории\nв днях'

}

DATE_COLUMNS_LIST = [
    'Дата_торгов',
    'Дата_исполнения',
    'Дата_погашения'
]

Form, Window = uic.loadUiType("SUBD.ui")
addForm, _ = uic.loadUiType("add_record_window.ui")
Directory = os.getcwd()
db_file = os.path.join(Directory, 'fond_db.db')


class DateDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        date = QDate.fromString(value, "yyyy-MM-dd")
        return date.toString("dd-MM-yyyy")


"""------------------------ФИЛЬТРЫ------------------------"""


def check1_change():
    if form.checkBox.isChecked():
        form.dop_lineEdit.setVisible(True)
    else:
        form.dop_lineEdit.setVisible(False)


def check2_change():
    if form.checkBox_2.isChecked():
        form.dop_lineEdit_2.setVisible(True)
    else:
        form.dop_lineEdit_2.setVisible(False)


def check3_change():
    if form.checkBox_3.isChecked():
        form.dop_lineEdit_3.setVisible(True)
    else:
        form.dop_lineEdit_3.setVisible(False)


def get_statements():
    return {
        'Дата_торгов': [form.lineEdit.text(), form.dop_lineEdit.text()],
        'Дата_исполнения': [form.lineEdit_2.text(), form.dop_lineEdit_2.text()],
        'Дата_погашения': [form.lineEdit_3.text(), form.dop_lineEdit_3.text()],
        'Число_продаж': [form.lineEdit_4.text()],
        'Текущая_цена': [form.lineEdit_5.text()],
        'Минимальная_цена': [form.lineEdit_6.text()],
        'Максимальная_цена': [form.lineEdit_7.text()],
        'Код_фьючерса': [getCheckedCheckBox()],
        'Код_серии': [form.comboBox_3.currentText()]
    }


def handle_statements(statements: Dict[str, list]) -> Dict[str, list]:
    handled_statements = dict()
    for column, raw_string in statements.items():
        statement = raw_string
        if statement != ['', ''] and statement != ['']:
            checkBox = None
            if column == 'Дата_торгов':
                checkBox = CHECK_LIST[0]
            elif column == 'Дата_исполнения':
                checkBox = CHECK_LIST[1]
            elif column == 'Дата_погашения':
                checkBox = CHECK_LIST[2]

            if column == 'Код_фьючерса':
                statement = raw_string[0]
                statement = ', '.join("'" + str(el) + "'" for el in statement)
                handled_statements[column] = f"{column} IN ({statement})"


            elif statement.count(' '):
                handled_statements[column] = f'{column} SPACE_ERROR'

            elif column == 'Код_серии':
                statement = raw_string[0].strip()
                if statement == 'Все':
                    continue
                handled_statements[column] = f"{column} = '{statement}'"
            elif statement.count(' '):
                handled_statements[column] = f'{column} SPACE_ERROR'

            elif column in DATE_COLUMNS_LIST and checkBox.isChecked() == True:
                statement_1 = statement[0]
                statement_2 = statement[1]
                for symbol in statement_1:
                    if symbol not in '' + '1234567890-':
                        handled_statements[column] = f"{column} DATE_CHECK_ERROR"
                        break
                for symbol in statement_2:
                    if symbol not in '' + '1234567890-':
                        handled_statements[column] = f"{column} DATE_CHECK_ERROR"
                        break
                if len(statement_1) > 10:
                    handled_statements[column] = f"{column} DATE_LENGTH_ERROR"
                    break
                if len(statement_2) > 10:
                    handled_statements[column] = f"{column} DATE_LENGTH_ERROR"
                    break
                statement_1 = '-'.join(statement_1.split('-')[::-1])
                try:
                    statement_1 = datetime.strptime(statement_1, '%Y-%m-%d')
                except ValueError:
                    handled_statements[column] = f"{column} DATE_SYMBOLS_ERROR"
                    break

                statement_2 = '-'.join(statement_2.split('-')[::-1])
                try:
                    statement_2 = datetime.strptime(statement_2, '%Y-%m-%d')
                except ValueError:
                    handled_statements[column] = f"{column} DATE_SYMBOLS_ERROR"
                    break

                if statement_2 < statement_1:
                    handled_statements[column] = f"{column} DATE_TIME_ERROR"
                    break
                handled_statements[
                    column] = f"{column} BETWEEN '{statement_1.strftime('%Y-%m-%d')}' AND '{statement_2.strftime('%Y-%m-%d')}'"

            elif column in DATE_COLUMNS_LIST and checkBox.isChecked() == False:
                statement = statement[0]
                if statement.startswith('='):
                    statement = statement.replace('=', '')
                for symbol in statement:
                    if symbol not in ''.join(LOGICAL_OPERATORS) + '1234567890-':
                        handled_statements[column] = f"{column} DATE_SYMBOLS_ERROR"
                        break
                else:
                    operator = 'LIKE'
                    for logical_operator in LOGICAL_OPERATORS:
                        if statement.startswith(logical_operator):
                            operator = logical_operator
                            statement = statement.replace(logical_operator, '')
                            break
                    if len(statement) > 10:
                        handled_statements[column] = f"{column} DATE_LENGTH_ERROR"
                    else:
                        statement = '-'.join(statement.split('-')[::-1])
                        try:
                            statement = datetime.strptime(statement, '%Y-%m-%d')

                        except ValueError:
                            handled_statements[column] = f"{column} DATE_SYMBOLS_ERROR"
                            break
                        handled_statements[column] = f"{column} {operator} '{statement.strftime('%Y-%m-%d')}'"

            else:
                statement = raw_string[0].strip()
                for logical_operator in LOGICAL_OPERATORS:
                    if statement.startswith(logical_operator):
                        operator = logical_operator
                        statement = statement.replace(logical_operator, '')
                        statement = statement.replace(',', '.')
                        handled_statements[column] = f"{column} {operator} {statement}"
                        break
                else:
                    if statement.isdecimal():
                        handled_statements[column] = f"{column} = {statement}"
                    else:
                        handled_statements[column] = f"{column} DECIMAL_ERROR"
    return handled_statements


def get_sql_filter():
    handled_statements = handle_statements(get_statements())
    filter_statements = list()
    errors = list()

    if handled_statements:
        for column, statement in handled_statements.items():
            if statement.endswith('ERROR'):
                errors.append(statement)
            else:
                filter_statements.append(statement)
        return ' AND '.join(filter_statements), errors
    return '', []


def error_filter_check(errors):
    columns = {
        'Дата_торгов': 'Дата торгов',
        'Дата_исполнения': 'Дата исполнения',
        'Дата_погашения': 'Дата погашения',
        'Число_продаж': 'Число продаж',
        'Текущая_цена': 'Текущая цена',
        'Минимальная_цена': 'Минимальная цена',
        'Максимальная_цена': 'Максимальная цена',
        'Код_серии': 'Код серии',
        'Код_фьючерса': 'Код фьючерса'
    }
    errors_list = list()
    for error in errors:

        column, error_type = error.split(' ')

        if error_type == 'SPACE_ERROR':
            errors_list.append(f'"{columns[column]}" заданы лишние символы пробела')

        elif error_type == 'DATE_LENGTH_ERROR':
            errors_list.append(f'"{columns[column]}" задана слишком длинная строка')

        elif error_type == 'DATE_SYMBOLS_ERROR':
            errors_list.append(f'"{columns[column]}" использованы некорректные символы')

        elif error_type == 'DATE_CHECK_ERROR':
            errors_list.append(f'"{columns[column]}" Введите 2 даты не используя никаких других символов')

        elif error_type == 'DATE_TIME_ERROR':
            errors_list.append(f'"{columns[column]}" Вводимая внизу дата должна быть больше чем верхняя')

        elif error_type == 'DECIMAL_ERROR':
            errors_list.append(f'"{columns[column]}" задано не десятичное число')
    return errors_list


def set_filter():
    filter_statement, errors = get_sql_filter()

    model.setFilter(filter_statement)

    if errors:
        errors_list = error_filter_check(errors)
        form.message = QMessageBox(QMessageBox.Icon.Warning, 'Ошибка в задании фильтра', '\n'.join(errors_list))
        form.message.show()


def clear_filter():
    form.lineEdit.clear()
    form.lineEdit_2.clear()
    form.lineEdit_3.clear()
    form.lineEdit_4.clear()
    form.lineEdit_5.clear()
    form.lineEdit_6.clear()
    form.lineEdit_7.clear()
    form.dop_lineEdit.clear()
    form.dop_lineEdit_2.clear()
    form.dop_lineEdit_3.clear()
    setAllState(True)

    form.comboBox_3.setCurrentIndex(0)
    set_filter()


"""------------------------УДАЛЕНИЕ СТРОКИ------------------------"""


def delete_row():
    selected_indexes = form.tableView.selectedIndexes()
    form.message = QMessageBox()
    if len(selected_indexes) > 0:
        form.message.setText("Вы уверены, что хотите удалить выделенные записи?")
        form.message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if form.message.exec() == form.message.StandardButton.Yes:
            for index in sorted(selected_indexes, reverse=True):
                model.removeRow(index.row())
            model.select()
        else:
            message_text = 'Удаление отменено'
            form.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка удаления', message_text)
            form.message.show()
    else:
        message_text = 'Не выбрана запись для удаления'
        form.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка удаления', message_text)
        form.message.show()


"""------------------------ДОБАВЛЕНИЕ/ИЗМЕНЕНИЕ СТРОКИ------------------------"""


def record_dialog(row_record: Tuple[int, QSqlRecord] = None):
    add_dialog = QDialog(window)
    add_ui = addForm()
    add_ui.setupUi(add_dialog)
    is_row_edit = True if row_record else False
    add_dialog.setWindowTitle("Редактирование записи" if is_row_edit else "Добавление записи")
    ok_button_text = 'Изменить' if is_row_edit else 'Добавить'
    add_ui.pushButton.setText(ok_button_text)
    add_ui.pushButton_2.setText('Отмена')
    row_to_edit, record = None, None
    if is_row_edit:
        row_to_edit, record = row_record
    else:
        record = model.record()

    query = QSqlQuery('SELECT Код_фьючерса, Код_серии, Дата_исполнения FROM Даты_исполнения_фьючерсов')
    cod_with_date_and_stat = dict()
    while query.next():
        cod_with_date_and_stat[query.value(0)] = query.value(1), query.value(2)
    add_ui.comboBox.addItems(cod_with_date_and_stat.keys())
    validator = QDoubleValidator(0, 9999, 2)
    validator_1 = QIntValidator(0, 9999)
    add_ui.lineEdit_4.setValidator(validator)
    add_ui.lineEdit_5.setValidator(validator)
    add_ui.lineEdit_6.setValidator(validator)
    add_ui.lineEdit_7.setValidator(validator_1)
    add_ui.message = None

    if is_row_edit:
        add_ui.comboBox.setCurrentIndex(add_ui.comboBox.findText(record.value("Код_фьючерса")))
        add_ui.lineEdit_2.setText('-'.join(record.value('Дата_торгов').split('-')[::-1]))
        add_ui.lineEdit_3.setText('-'.join(record.value('Дата_погашения').split('-')[::-1]))
        add_ui.lineEdit_4.setText(str(record.value('Текущая_цена')).replace('.', ','))
        add_ui.lineEdit_5.setText(str(record.value('Минимальная_цена')).replace('.', ','))
        add_ui.lineEdit_6.setText(str(record.value('Максимальная_цена')).replace('.', ','))
        add_ui.lineEdit_7.setText(str(record.value('Число_продаж')))

    def add_record():
        f_code = add_ui.comboBox.currentText()
        exec_date = cod_with_date_and_stat[f_code][1]
        exec_date = datetime.strptime(exec_date, '%d-%m-%Y')
        serial_number = cod_with_date_and_stat[f_code][0]
        torg_date = add_ui.lineEdit_2.text()
        torg_date = "-".join(torg_date.split('-'))
        if len(torg_date) != 10:
            message_text = f'"Дата торгов"\nЗаполните поле корректно'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        try:
            torg_date = datetime.strptime(torg_date, '%d-%m-%Y')
        except ValueError:
            message_text = f'"Дата торгов"\nВведите существующую дату'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        if torg_date >= exec_date:
            message_text = f'"Дата торгов"\nВведите дату меньшую даты исполнения: {exec_date}'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        maturity_date = add_ui.lineEdit_3.text()
        maturity_date = '-'.join(maturity_date.split('-'))
        if len(maturity_date) != 10:
            message_text = f'"Дата погашения"\nЗаполните поле корректно'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        try:
            maturity_date = datetime.strptime(maturity_date, '%d-%m-%Y')
        except ValueError:
            message_text = f'"Дата погашения"\nВведите существующую дату'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return

        if torg_date >= maturity_date:
            message_text = f'"Дата торгов"\nВведите дату большую даты торгов: {maturity_date} {torg_date}'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        if exec_date > maturity_date:
            message_text = f'"Дата погашения"\nВведите дату большую даты исполнения: {exec_date}'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка ', message_text)
            add_ui.message.show()
            return
        try:
            sales = int(add_ui.lineEdit_7.text())
        except ValueError:
            message_text = f'"Число продаж"\nЗаполните поле, если продаж нет поставьте 0'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        try:
            value = float(str(add_ui.lineEdit_4.text()).replace(',', '.'))
        except ValueError:
            message_text = f'"Текущая цена"\nЗаполните поле'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        try:
            min_value = float(str(add_ui.lineEdit_5.text()).replace(',', '.'))
        except ValueError:
            message_text = f'"Минимальная цена"\nЗаполните поле'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        try:
            max_value = float(str(add_ui.lineEdit_6.text()).replace(',', '.'))
        except ValueError:
            message_text = f'"Максимальная цена"\nЗаполните поле'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        if value and min_value and max_value:
            if max_value < min_value:
                message_text = f'"Цена"\nМаксимальная цена не может быть меньше минимальной'
                add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
                add_ui.message.show()
                return
            if value < min_value:
                message_text = f'"Цена"\nТекущая цена не может быть меньше минимальной' \
                               f'\nИзмените минимальную цену или поставьте текущую выше минимальной'
                add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
                add_ui.message.show()
                return
            if value > max_value:
                message_text = f'"Цена"\nТекущая цена не может быть больше максимальной' \
                               f'\nИзмените максимальную цену или поставьте текущую ниже максимальной'
                add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
                add_ui.message.show()
                return
        record.setValue("Дата_торгов", torg_date.strftime('%Y-%m-%d'))
        record.setValue("Дата_исполнения", exec_date.strftime('%Y-%m-%d'))
        record.setValue("Дата_погашения", maturity_date.strftime('%Y-%m-%d'))
        record.setValue("Число_продаж", sales)
        record.setValue("Текущая_цена", value)
        record.setValue("Минимальная_цена", min_value)
        record.setValue("Максимальная_цена", max_value)
        record.setValue("Код_серии", serial_number)
        record.setValue("Код_фьючерса", f_code)

        if is_row_edit:
            model.setRecord(row_to_edit, record)
        else:
            model.insertRecord(0, record)

        model.submitAll()
        model.select()
        add_dialog.accept()

    add_ui.pushButton.clicked.connect(add_record)
    add_ui.pushButton_2.clicked.connect(add_dialog.close)
    add_dialog.exec()


"""------------------------ПОДКЛЮЧЕНИЕ БД------------------------"""


def connect_db(db_file):
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(db_file)
    if not db.open():
        print("Cannot establish a database connection to {}!".format(db_file))
        return False
    return db


"""------------------------ОТКРЫТИЕ ОКНА ДОБАВЛЕНИЯ/ИЗМЕНЕНИЯ------------------------"""


def open_add_record_window():
    record_dialog()


def open_edit_record_window():
    selected_indexes = form.tableView.selectedIndexes()
    if selected_indexes:
        row = selected_indexes[0].row()
        record = model.record(row)
        record_dialog((row, record))


def con_read_table():
    conn = connect('fond_db.db')
    df = pd.read_sql('SELECT * FROM Общая_таблица', conn)
    conn.close()
    return df


def raschet():
    df = con_read_table()

    date_columns = ['Дата_торгов', 'Дата_исполнения', 'Дата_погашения']
    df[date_columns] = df[date_columns].apply(lambda x: pd.to_datetime(x, format='%Y-%m-%d'))
    future_tables = {}
    for future in df['Код_фьючерса'].unique():
        future_tables[future] = df[df['Код_фьючерса'] == future][
            ['Код_фьючерса', 'Дата_торгов', 'Дата_исполнения', 'Дата_погашения',
             'Число_продаж', 'Текущая_цена', 'Минимальная_цена', 'Максимальная_цена',
             'Код_серии']]
        future_tablica = future_tables[future]
        future_tablica.sort_values(by='Дата_торгов')

        day_delta = (future_tablica['Дата_исполнения'].iloc[0] - future_tablica['Дата_погашения'].iloc[0]).days

        future_tablica['rk'] = np.log((future_tablica['Текущая_цена'] / 100)) / day_delta
        xk_list = [0, 0]
        if len(future_tablica) > 2:
            for i in range(2, len(future_tablica)):
                xk_list.append(np.log(future_tablica['rk'].iloc[i] / future_tablica['rk'].iloc[i - 2]))
            future_tablica['xk'] = xk_list
        else:
            future_tablica['xk'] = 0
        future_tablica['Дата_исполнения'] = pd.to_datetime(future_tablica['Дата_исполнения']).dt.strftime('%d-%m-%Y')
        future_tablica['Дата_торгов'] = pd.to_datetime(future_tablica['Дата_торгов']).dt.strftime('%d-%m-%Y')

    temp = pd.DataFrame()
    for future in future_tables.values():
        temp = pd.concat([future, temp])
    future_tables['Все'] = temp
    return future_tables


def show_table(df):
    model123 = QSqlTableModel()
    global data_T

    if not df:

        model123.clear()
        model123.select()
        form.tableView_2.setModel(model123)
        return 1
    keys_list = [key for key in df.keys() if key != 'Все']
    name = 'rk_table1'
    data_T_dict = {}
    for key in keys_list:
        if df[key].empty:
            data_T_dict[key] = pd.Series(['Нет торгов с указанным фильтром'])
        else:
            data_T_dict[key] = pd.Series(df[key]['xk'].values)
    data_T = pd.DataFrame(data_T_dict, columns=keys_list)

    with sql.connect('fond_db.db', timeout=30) as connect:
        data_T.to_sql(name=name, con=connect, if_exists='replace', chunksize=10, index=False)

    model123.setTable(name)
    model123.select()

    form.tableView_2.setSortingEnabled(False)
    form.tableView_2.setModel(model123)


def add_checkboxes(df):
    form.scrollAreaWidgetContents = QWidget()
    form.scrollAreaWidgetContents.setObjectName('scroll')
    form.layout = QVBoxLayout(form.scrollAreaWidgetContents)
    form.layout.setObjectName('layout')
    form.list_check_boxes = []
    form.layout.addWidget(checkall)
    form.list_check_boxes.append(checkall)

    for col_name in df['Все']['Код_фьючерса'].unique():
        checkBox = QCheckBox(f'{col_name}')
        checkBox.setObjectName(f'{col_name}')
        form.layout.addWidget(checkBox)
        form.list_check_boxes.append(checkBox)
    form.scrollArea.setWidget(form.scrollAreaWidgetContents)


def setAllState(state):
    for checkBox in form.list_check_boxes:
        checkBox.setChecked(state)


def getCheckedCheckBox():
    return [checkBox.objectName() for checkBox in form.list_check_boxes if
            checkBox.isChecked() and checkBox.objectName() != 'Все']


def replace_specific_in_clause(sql_query, values_to_replace, replace_value='all'):
    pattern = re.compile(
        f'IN\\s*\\(\\s*\'({"|".join(values_to_replace)})\'(?:\\s*,\\s*\'({"|".join(values_to_replace)})\')*\\s*\\)')
    match = pattern.search(sql_query)

    if match:
        replaced_query = sql_query[:match.start()] + f'IN \'{replace_value}\'' + sql_query[match.end():]
        return replaced_query
    else:
        return sql_query


def parse_numeric_condition(condition_str):
    pattern = re.compile(r'([<>]=?)?(\d+)')
    match = pattern.match(condition_str)

    if match:
        operator = match.group(1)
        numeric_value = int(match.group(2))

        return operator, numeric_value
    else:
        return None, None


def parse_date_condition(condition_str):
    pattern = re.compile(r'([<>]=?)?([^<>]+)')
    match = pattern.match(condition_str)

    if match:
        operator = match.group(1)
        date_str = match.group(2)

        try:
            date_value = datetime.strptime(date_str, '%d-%m-%Y').date()
            return operator, date_value
        except ValueError:
            return None, None
    else:
        return None, None


def apply_filter(df, filter_statement):
    mask = pd.Series(True, index=df.index)
    """df['Дата_торгов'] = pd.to_datetime(df['Дата_торгов'],
                                                format='%d-%m-%Y')"""
    for column, conditions in filter_statement.items():
        if column in df.columns and any(conditions):
            if column == 'Код_серии':
                if conditions[0] != 'Все':
                    mask &= df[column].isin(conditions)
            elif column == 'Код_фьючерса':
                mask &= df[column].isin(conditions[0])
            elif column in ['Максимальная_цена', 'Минимальная_цена', 'Текущая_цена', 'Число_продаж']:
                operator, value = parse_numeric_condition(conditions[0])

                if operator is not None and value is not None:
                    if operator == '>':
                        mask &= df[column] > value
                    elif operator == '<':
                        mask &= df[column] < value
                    elif operator == '=':
                        mask &= df[column] == value
                    elif operator == '>=':
                        mask &= df[column] >= value
                    elif operator == '<=':
                        mask &= df[column] <= value
            else:
                if isinstance(conditions[0], str):
                    first_day = '-'.join(conditions[0].split('-')[::-1])
                else:
                    first_day = conditions[0].strftime('%d-%m-%Y')
                    first_day = '-'.join(first_day.split('-')[::-1])
                if isinstance(conditions[1], str):

                    last_day = '-'.join(conditions[1].split('-')[::-1])
                else:
                    last_day = conditions[1].strftime('%d-%m-%Y')
                    last_day = '-'.join(last_day.split('-')[::-1])

                if len(conditions[1]) == 0:
                    mask &= (df[column] == first_day)
                else:
                    try:
                        mask &= df[column].between(first_day, last_day)
                    except TypeError:

                        break

    filtered_df = df[mask]
    return filtered_df


def show_filter(sql_query):
    all = False
    for checkBox in form.list_check_boxes:
        if checkBox.objectName() == 'Все':
            if checkBox.isChecked():
                all = True
    if all:
        values_to_replace = ['21057-1602', '22020-1602', '22020-1503', '22020-1904', '21058-1503',
                             '21058-2903', '22021-2903', '22023-1203', '22023-1705', '22024-1406',
                             '22019-0904', '22024-0904', '22024-2304', '22028-1907', '22024-3004',
                             '22028-3105', '22024-0705', '22024-2105', '22024-0406', '22027-0207',
                             '22032-0608', '22034-2008', '22024-2506', '22024-0207', '22037-0309',
                             '22024-0907', '22027-1607', '22032-1607', '22036-1709', '22024-1607',
                             '22036-1607', '22039-0608', '22038-0110', '22039-1510', '22036-2708',
                             '22036-1009', '22040-2910', '22044-0511', '22047-0511', '22039-0810',
                             '22043-1911', '22044-0312', '22045-1911', '22047-0312', '22049-1911',
                             '22051-2412', '22052-1401']

        sql_query = replace_specific_in_clause(sql_query, values_to_replace, replace_value='Все фьючерсы')


def get_dates_for_columns(date_dict, checkbox_states):
    result = {}
    has_errors = False

    for key, dates in date_dict.items():
        first_date, second_date = dates

        checkbox_state = checkbox_states[list(date_dict.keys()).index(key)]

        if not first_date and not second_date and checkbox_state:
            result[key] = {'dates': [], 'error': f"Ошибка: Вы не указали обе даты для {key}", 'full_period': False,
                           'operator': ''}
            has_errors = True
        elif first_date and not second_date and checkbox_state:
            result[key] = {'dates': [], 'error': f"Ошибка: Вы не указали вторую дату для {key}", 'full_period': False,
                           'operator': ''}
            has_errors = True
        elif not first_date and second_date and checkbox_state:
            result[key] = {'dates': [], 'error': f"Ошибка: Вы не указали первую дату для {key}", 'full_period': False,
                           'operator': ''}
            has_errors = True
        elif first_date and second_date and checkbox_state:
            result[key] = {'dates': [first_date, second_date], 'error': "", 'full_period': False, 'operator': ''}
        elif not first_date and not second_date and not checkbox_state:
            result[key] = {'dates': [], 'error': "", 'full_period': True, 'operator': ''}
        elif first_date and not second_date and not checkbox_state:
            first_operator, first_date_without_operator = parse_date_condition(first_date)
            result[key] = {'dates': [first_date_without_operator], 'error': "", 'full_period': False,
                           'operator': f'{first_operator}'}
        else:
            result[key] = {'dates': [], 'error': "", 'full_period': False, 'operator': ''}

    return result, has_errors


def process_date_column(df, feat_name, column, date_format='%d-%m-%Y'):
    df[feat_name][column] = pd.to_datetime(df[feat_name][column], format=date_format)
    min_date = df[feat_name][column].min().strftime(date_format)
    max_date = df[feat_name][column].max().strftime(date_format)
    return min_date, max_date


def update_filter_for_operators(filter_statement, key, operator, dates, min_max_date_dict):
    if operator == '>':
        first_day = dates[0]
        first_day += timedelta(days=1)
        filter_statement[key] = [first_day.strftime('%d-%m-%Y'), min_max_date_dict[key]['max_date']]
    elif operator == '<':
        last_day = dates[0]
        last_day -= timedelta(days=1)
        filter_statement[key] = [min_max_date_dict[key]['min_date'], last_day.strftime('%d-%m-%Y')]
    elif operator == '=':
        filter_statement[key] = [dates[0].strftime('%d-%m-%Y'), '']
    elif operator == '>=':
        filter_statement[key] = [dates[0].strftime('%d-%m-%Y'), min_max_date_dict[key]['max_date']]
    elif operator == '<=':
        filter_statement[key] = [min_max_date_dict[key]['min_date'], dates[0].strftime('%d-%m-%Y')]


def stat_xap_test(df):
    tabl = {}
    df_filtered_dict = {}
    feat_names = []
    filter_statement = get_statements()
    checkbox_states = [form.checkBox.isChecked(), form.checkBox_2.isChecked(), form.checkBox_3.isChecked()]
    date_keys = ['Дата_торгов', 'Дата_исполнения', 'Дата_погашения']
    date_dict = {key: filter_statement[key] for key in date_keys if key in filter_statement}

    date_conditions, date_errors = get_dates_for_columns(date_dict, checkbox_states)
    filters, errors = get_sql_filter()
    errors_to_show = error_filter_check(errors)
    if errors:
        return errors_to_show[0], {}
    if date_errors:
        first_error = next((value['error'] for value in date_conditions.values() if value['error'].strip()), None)
        return first_error, {}

    full_period = all(dates_info['full_period'] for dates_info in date_conditions.values())

    if full_period:
        feat_names = df['Все']['Код_фьючерса'].unique()
    else:
        for key, dates_info in date_conditions.items():
            dates = dates_info['dates']
            if key == 'Дата_торгов':
                if len(dates) == 2:
                    day_t = dates[1]
                    temp = df['Все'][df['Все']['Дата_торгов'] == day_t]
                    feat_names = temp['Код_фьючерса'].unique()
                elif len(dates) == 1:
                    if len(dates_info['operator']) != 0:
                        temp = df['Все'][df['Все']['Код_фьючерса'].isin(filter_statement['Код_фьючерса'][0])]
                        feat_names = temp['Код_фьючерса'].unique()
                    else:
                        day_t = dates[0].strftime('%d-%m-%Y')
                        temp = df['Все'][df['Все']['Дата_торгов'] == day_t]
                        feat_names = temp['Код_фьючерса'].unique()
                        filter_statement['Дата_торгов'] = [dates[0],
                                                           '']
                elif len(dates) == 0:
                    return 'Вы не ввели дату торгов', {}

    feat_names = list(feat_names)

    if not feat_names and any(checkbox_states):
        return 'Вы поставили галочку, но оставили поле пустым. Уберите галочку', {}

    filtered_feat_names = [feature_name for column, conditions in filter_statement.items()
                           if column == 'Код_фьючерса' for feature_name in conditions[0] if
                           feature_name in feat_names]
    for feat_name in filtered_feat_names:

        min_max_date_dict = {
            column: {
                'min_date': process_date_column(df, feat_name, column)[0],
                'max_date': process_date_column(df, feat_name, column)[1]
            } for column in date_keys
        }

        for key, dates_info in date_conditions.items():
            operator = dates_info['operator']
            dates = dates_info['dates']
            if len(operator) != 0:
                update_filter_for_operators(filter_statement, key, operator, dates, min_max_date_dict)

        if full_period:
            filter_statement['Дата_торгов'] = [min_max_date_dict['Дата_торгов']['min_date'],
                                               min_max_date_dict['Дата_торгов']['max_date']]
        df_filtered = apply_filter(df[feat_name], filter_statement)

        if df_filtered.empty:
            df_filtered_dict[feat_name] = pd.DataFrame()
            min, max, mean, date_start, length = 0, 0, 0, '---', 'Нет торгов с указанным фильтром'
        else:
            df_filtered_dict[feat_name] = df_filtered
            min, max, mean = df_filtered['xk'].min(), df_filtered['xk'].max(), df_filtered['xk'].mean()
            date_start, length = df_filtered['Дата_торгов'].iloc[0].strftime('%d-%m-%Y'), len(df_filtered)

        stat = {'min': min, 'max': max, 'mean': mean, 'Дата_начала_торгов': date_start, 'len': length}
        tabl[feat_name] = stat

    return tabl, df_filtered_dict


def add_records_stat(model1, df):
    global df_for_save
    db.open()
    stata, df_dict_to_show = stat_xap_test(df)
    df_dict_to_show = {key: value for key, value in df_dict_to_show.items() if not value.empty}  # удаление пустых

    show_table(df_dict_to_show)
    if not stata:
        stata = {'Ошибка': {'len': 'В последний день выбранного диапазона не было торгов',
                            'max': 0,
                            'mean': 0,
                            'min': 0,
                            'Дата_начала_торгов': ''}}

    elif isinstance(stata, str):
        stata = {'Ошибка': {'len': stata,
                            'max': 0,
                            'mean': 0,
                            'min': 0,
                            'Дата_начала_торгов': ''}}

    form.lineEdit_8.setText('')
    if model1.rowCount() != 0:
        while model1.rowCount() > 0:
            model1.removeRow(0)
            model1.select()

    df_for_save = pd.DataFrame(
        columns=["Код_фьючерса", "Минимум", "Максимум", "Среднее", "Дата_начала_торгов", "Длина предыстории в днях"])
    for name, stats in stata.items():
        if stats['len'] == 'Нет торгов с указанным фильтром':
            continue
        new_row = [name, round(float(stats.get('min', 0)), 5),
                   round(float(stats.get('max', 0)), 5),
                   round(float(stats.get('mean', 0)), 5),
                   stats.get('Дата_начала_торгов', ''),
                   stats.get('len', '')]

        df_for_save.loc[len(df_for_save.index)] = new_row

        r = model1.record()
        r.setValue("Код_фьючерса", new_row[0])
        r.setValue("min", new_row[1])
        r.setValue("max", new_row[2])
        r.setValue("mean", new_row[3])
        r.setValue("Дата_начала_торгов", new_row[4])
        r.setValue("len", new_row[5])
        model1.insertRecord(-1, r)
        model1.select()
    set_filter()


def norm_test(df):
    stata, df_dict_to_show = stat_xap_test(df)
    max_len_key = max(stata, key=lambda x: stata[x]['len'])
    data_to_test = df[max_len_key]['xk']
    if kstest(data_to_test, 'norm').pvalue < 0.05:
        res = f'Контролируемый показатель фьючерса {max_len_key} распределен ненормально'
    else:
        res = f'Контролируемый показатель фьючерса {max_len_key} распределен нормально'
    form.lineEdit_8.setText(res)


def create_empty_table(stata=False, rk=False):
    name = 'stat'
    stat_empty = pd.DataFrame(columns=['Код_фьючерса', 'min', 'max', 'mean', 'Дата_начала_торгов', 'len'])
    connect = sql.connect('fond_db.db')
    stat_empty.to_sql(name=name, con=connect, if_exists='replace', index=False)
    connect.close()
    model2 = QSqlTableModel()
    model2.setTable(name)
    for i in range(model2.columnCount()):
        header_data = model2.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        column_name = COLUMNS_DICT[header_data]

        model2.setHeaderData(i, Qt.Orientation.Horizontal, column_name, Qt.ItemDataRole.DisplayRole)
        model2.setHeaderData(i, Qt.Orientation.Horizontal, header_data, Qt.ItemDataRole.UserRole)

    model2.select()

    form.tableView_3.setSortingEnabled(False)
    form.tableView_3.setModel(model2)

    return model2


def make_plot(df):
    stata, df_dict_to_show = stat_xap_test(df)
    df_dict_to_show = {key: value for key, value in df_dict_to_show.items() if not value.empty}

    form.message = QMessageBox()
    if len(df_dict_to_show) > 7:
        form.message.setIcon(QMessageBox.Icon.Warning)
        form.message.setText("Много фьючерсов, график может быть не информативен. ")
        form.message.setInformativeText("Вы уверены, что хотите построить график?")
        form.message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if form.message.exec() == form.message.StandardButton.Yes:
            fig, ax = plt.subplots()
            for key in df_dict_to_show:
                data = df_dict_to_show[key]
                data['Дата_торгов'] = pd.to_datetime(data['Дата_торгов'], format='%d-%m-%Y')
                data.sort_values(by='Дата_торгов')
                x = list(data['Дата_торгов'].values)
                y = list(data['xk'].values)
                ax.plot(x, y, label=key)
            ax.set_xlabel('Дата')
            ax.set_ylabel('Основной контролируемый показатель')
            ax.set_title("График показателей качества:")
            ax.legend()
            plt.show()

    else:
        fig, ax = plt.subplots()
        for key in df_dict_to_show:
            data = df_dict_to_show[key]
            data['Дата_торгов'] = pd.to_datetime(data['Дата_торгов'], format='%d-%m-%Y')
            data.sort_values(by='Дата_торгов')
            x = list(data['Дата_торгов'].values)
            y = list(data['xk'].values)
            ax.plot(x, y, label=key)
            ax.set_xlabel('Дата')
            ax.set_ylabel('Основной контролируемый показатель')
            ax.set_title("График показателей качества:")
            ax.legend()
            plt.show()


def save_files():
    dialog = QFileDialog()
    dialog.setNameFilter("Excel File (*.xlsx)")
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Сохранить")
    dialogsuccessful = dialog.exec()
    filelocation = ''
    if dialogsuccessful:
        filelocation = dialog.selectedFiles()[0]

    filter_statement = get_statements()
    filters_for_print = {key: value for key, value in filter_statement.items() if
                         key != 'Код_фьючерса' and value not in (['', ''], [''])}
    filters_to_xlsx = ', '.join([f'{key}: {value[0]}' for key, value in filters_for_print.items()])

    with pd.ExcelWriter(filelocation + '.xlsx') as excel_writer:
        worksheet_stroka = excel_writer.book.add_worksheet('Фильтры')
        worksheet_stroka.write(0, 0, 'Фильтры:' + filters_to_xlsx)

        df_for_save.to_excel(excel_writer, sheet_name='Основные статистики xk', index=False)

        data_T.to_excel(excel_writer, sheet_name='Показатель xk', index=False)

    excel_writer.save()


def save_file():
    options = QFileDialog.Option.DontUseNativeDialog
    filelocation, _ = QFileDialog.getSaveFileName(None, "Save File", "", "Excel File (*.xlsx)",
                                                  options=options)

    if filelocation == '':
        form.message = QMessageBox()
        form.message.setIcon(QMessageBox.Icon.Warning)
        form.message.setText("Сохранение отменено")
        form.message.show()
    else:

        filter_statement = get_statements()
        filter_statement['Код_фьючерса'] = filter_statement['Код_фьючерса'][0]
        if filter_statement['Дата_исполнения'][1] != '':
            filter_statement['Дата_исполнения'] = ['От ' + str(filter_statement['Дата_исполнения'][0]),
                                                   'до ' + str(filter_statement['Дата_исполнения'][1])]

        if filter_statement['Дата_торгов'][1] != '':
            filter_statement['Дата_торгов'] = ['От ' + str(filter_statement['Дата_торгов'][0]),
                                               'до ' + str(filter_statement['Дата_торгов'][1])]

        if filter_statement['Дата_погашения'][1] != '':
            filter_statement['Дата_погашения'] = ['От ' + str(filter_statement['Дата_погашения'][0]),
                                                  'до ' + str(filter_statement['Дата_погашения'][1])]

        max_length = max(len(lst) for lst in filter_statement.values())
        fixed_data = {key: (value + [''] * (max_length - len(value))) if isinstance(value, list) else value for
                      key, value
                      in filter_statement.items()}
        fldf = pd.DataFrame(fixed_data)

        if "Ошибка" in df_for_save["Код_фьючерса"][0]:
            form.message = QMessageBox()
            form.message.setIcon(QMessageBox.Icon.Warning)
            form.message.setText("Ошибка")
            form.message.show()
        else:

            if filelocation[-5:] == '.xlsx':
                fname = filelocation
            else:
                fname = filelocation + '.xlsx'
            with pd.ExcelWriter(fname) as excel_writer:
                fldf.to_excel(excel_writer, sheet_name='Фильтры', index=False)
                worksheet = excel_writer.sheets['Фильтры']
                worksheet.set_column('A:I', 20)
                df_for_save.to_excel(excel_writer, sheet_name='Основные статистики xk', index=False)
                data_T.to_excel(excel_writer, sheet_name='Показатель xk', index=False)
                excel_writer._save()


app = QApplication([])
window = Window()
form = Form()
form.setupUi(window)
form.message = None

db = connect_db(db_file)
if not db:
    sys.exit(-1)
else:
    print("connection ok")

df_dict = raschet()
model_4 = create_empty_table()

model = QSqlTableModel()
model.setTable('Общая_таблица')

for i in range(model.columnCount()):
    header_data = model.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
    column_name = COLUMNS_DICT[header_data]
    model.setHeaderData(i, Qt.Orientation.Horizontal, column_name, Qt.ItemDataRole.DisplayRole)
    model.setHeaderData(i, Qt.Orientation.Horizontal, header_data, Qt.ItemDataRole.UserRole)

model.select()

"""------------------------КНОПКИ ТАБЛИЦЫ + ЕЁ ИЗМЕНЕНИЙ------------------------"""

form.tableView.setSortingEnabled(True)
form.tableView_2.setSortingEnabled(True)
form.tableView.setModel(model)
date_delegate = DateDelegate()
form.tableView.setItemDelegateForColumn(1, date_delegate)
form.tableView.setItemDelegateForColumn(2, date_delegate)
form.tableView.setItemDelegateForColumn(3, date_delegate)
form.pushButton.clicked.connect(open_add_record_window)
form.pushButton_2.clicked.connect(open_edit_record_window)
form.pushButton_3.clicked.connect(delete_row)

"""------------------------КНОПКИ ФИЛЬТРОВ------------------------"""

query = QSqlQuery('SELECT Код_фьючерса FROM Даты_исполнения_фьючерсов')
cod_list = ['Все']
serial_list = set()
query_2 = QSqlQuery('SELECT Код_серии FROM Даты_исполнения_фьючерсов')
while query.next():
    cod_list.append(query.value(0))
while query_2.next():
    serial_list.add(query_2.value(0))
serial_list = list(serial_list)
serial_list.sort()
serial_list.insert(0, 'Все')
form.comboBox_3.addItems(serial_list)

form.pushButton_4.clicked.connect(set_filter)
form.pushButton_4.clicked.connect(lambda: add_records_stat(model_4, df_dict))  # статистика
form.pushButton_5.clicked.connect(clear_filter)
form.pushButton_8.clicked.connect(lambda: norm_test(df_dict))  # тест 'проверить'

CHECK_LIST = [form.checkBox, form.checkBox_2, form.checkBox_3]

form.checkBox.stateChanged.connect(check1_change)
form.checkBox_2.stateChanged.connect(check2_change)
form.checkBox_3.stateChanged.connect(check3_change)

form.dop_lineEdit.setVisible(False)
form.dop_lineEdit_2.setVisible(False)
form.dop_lineEdit_3.setVisible(False)

checkall = QCheckBox(f'Все')
checkall.setObjectName(f'Все')
add_checkboxes(df_dict)
setAllState(True)
checkall.stateChanged.connect(setAllState)
model.setFilter("Код_фьючерса")

form.pushButton_7.clicked.connect(lambda: make_plot(df_dict))
form.pushButton_9.clicked.connect(save_file)
"""------------------------ПОКАЗ ОКНА ПРИЛОЖЕНИ(ВРОДЕ)------------------------"""

window.show()
app.exec()
