"""Daily and Jalali monthly sales reporting, using recorded sale snapshots."""
from datetime import date


def report_sales(data, start, end):
    return sorted((s for s in data.get('sales', [])
                   if not s.get('cancelled') and start <= s['date'] <= end),
                  key=lambda s: (s['date'], s.get('productName', '')))


def jalali_range(day, mode):
    import jdatetime
    selected = jdatetime.date.fromgregorian(date=date.fromisoformat(day))
    if mode == 'day':
        return day, day
    start_day = 15 if mode == 'second' else 1
    if mode == 'first':
        last_day = 15
    elif selected.month <= 6:
        last_day = 31
    elif selected.month <= 11:
        last_day = 30
    else:
        last_day = 30 if selected.isleap() else 29
    first = selected.replace(day=start_day).togregorian().isoformat()
    last = selected.replace(day=last_day).togregorian().isoformat()
    return first, last


def show_general_report(app, Calendar, fa, jd, money, today):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QPushButton, QLabel, QHBoxLayout, QButtonGroup,
                                   QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QVBoxLayout,
                                   QTabWidget, QFormLayout, QLineEdit, QSpinBox, QAbstractSpinBox)
    dialog, layout = app.dialog('گزارش کلی')
    dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dialog.resize(1160, 650)
    state = {'day': today(), 'mode': 'day'}
    top = QHBoxLayout()
    layout.addLayout(top)
    choose = QPushButton()
    top.addWidget(choose)
    current = QPushButton('امروز')
    top.addWidget(current)
    top.addStretch()
    filters = QHBoxLayout()
    layout.addLayout(filters)
    group = QButtonGroup(dialog)
    group.setExclusive(True)
    for mode, label in [('day', 'روز انتخاب‌شده'), ('month', 'کل ماه'),
                        ('first', '۱ تا ۱۵ ماه'), ('second', '۱۵ تا پایان ماه')]:
        button = QPushButton(label)
        button.setCheckable(True)
        button.setChecked(mode == 'day')
        group.addButton(button)
        filters.addWidget(button)
        def select_mode(checked=False, mode=mode):
            state['mode'] = mode
            refresh()
        button.clicked.connect(select_mode)
    tabs = QTabWidget()
    tabs.setObjectName('settingsTabs')
    layout.addWidget(tabs, 1)
    sales_page = QWidget()
    sales_layout = QVBoxLayout(sales_page)
    tabs.addTab(sales_page, 'فروش')
    period = QLabel()
    period.setAlignment(Qt.AlignCenter)
    layout.addWidget(period)
    table = QTableWidget(0, 9)
    table.setHorizontalHeaderLabels(['تاریخ', 'نام کالا', 'روش فروش', 'تعداد',
                                    'خرید هر واحد', 'فروش هر واحد', 'سود هر واحد',
                                    'سود کل', 'مبلغ کل فروش'])
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionMode(QTableWidget.NoSelection)
    table.verticalHeader().hide()
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setWordWrap(True)
    sales_layout.addWidget(table, 1)
    total = QLabel()
    total.setAlignment(Qt.AlignCenter)
    total.setWordWrap(True)
    total.setStyleSheet('font-size:17px;font-weight:bold;color:#16844a;padding:12px;')
    sales_layout.addWidget(total)
    CHANNELS = {'digikala':'دیجیکالا','arazman':'آرازمان','basalam':'باسلام','snappshop':'اسنپ شاپ','inperson':'حضوری','instagram':'اینستاگرام','rubika':'روبیکا','telegram':'تلگرام','bale':'بله'}
    def rounded(value):
        import math
        return math.floor(value + .5)
    buy_page = QWidget()
    buy_layout = QVBoxLayout(buy_page)
    tabs.addTab(buy_page, 'خرید')
    form = QFormLayout()
    buy_layout.addLayout(form)
    name = QLineEdit()
    name.setPlaceholderText('نام کالای خریداری‌شده')
    quantity_input, cost_input = QSpinBox(), QSpinBox()
    quantity_input.setRange(1, 2000000000)
    cost_input.setRange(0, 2000000000)
    for control in [quantity_input, cost_input]:
        control.setButtonSymbols(QAbstractSpinBox.NoButtons)
        control.setGroupSeparatorShown(True)
    form.addRow('نام کالا', name)
    form.addRow('تعداد خرید', quantity_input)
    form.addRow('قیمت خرید هر واحد (تومان)', cost_input)
    buy_notice = QLabel('تاریخ خرید، همان تاریخ انتخاب‌شده بالای پنجره است.')
    buy_notice.setWordWrap(True)
    buy_layout.addWidget(buy_notice)
    add = QPushButton('افزودن خرید')
    buy_layout.addWidget(add)
    buy_table = QTableWidget(0, 5)
    buy_table.setHorizontalHeaderLabels(['تاریخ', 'نام کالا', 'تعداد', 'خرید هر واحد', 'مجموع خرید'])
    buy_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    buy_table.verticalHeader().hide()
    buy_table.setEditTriggers(QTableWidget.NoEditTriggers)
    buy_table.setSelectionMode(QTableWidget.NoSelection)
    buy_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    buy_layout.addWidget(buy_table, 1)
    buy_total = QLabel()
    buy_total.setAlignment(Qt.AlignCenter)
    buy_total.setStyleSheet('font-size:17px;font-weight:bold;padding:12px;')
    buy_layout.addWidget(buy_total)
    def add_purchase():
        import uuid
        if not name.text().strip():
            buy_notice.setText('نام کالا را وارد کنید.')
            return
        app.data.setdefault('generalPurchases', []).append(dict(id=str(uuid.uuid4()), date=state['day'], productName=name.text().strip(), quantity=quantity_input.value(), unitPrice=cost_input.value()))
        app.persist()
        name.clear()
        quantity_input.setValue(1)
        cost_input.setValue(0)
        buy_notice.setText('خرید ثبت شد؛ موجودی و قیمت‌های مانیتور تغییر نکردند.')
        refresh()
    add.clicked.connect(add_purchase)

    def refresh():
        choose.setText('انتخاب تاریخ: ' + fa(jd(state['day'])))
        start, end = jalali_range(state['day'], state['mode'])
        period.setText('از ' + fa(jd(start)) + ' تا ' + fa(jd(end)))
        rows = report_sales(app.data, start, end)
        table.setRowCount(len(rows))
        profits, unknown = [], 0
        for row, sale in enumerate(rows):
            profit = app.profit(sale)
            if profit is None:
                unknown += 1
            else:
                profits.append(profit)
            quantity = sale['quantity']
            values = [fa(jd(sale['date'])), sale.get('productName', '—'),
                      CHANNELS.get(sale['channel'], sale['channel']), fa(quantity),
                      money(sale.get('purchasePriceAtSale')), money(sale['unitPrice']),
                      money(rounded(profit / quantity) if profit is not None and quantity else None),
                      money(profit), money(sale['totalPrice'])]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setToolTip(value)
                table.setItem(row, column, item)
            table.setRowHeight(row, 60)
        text = 'مجموع سود: ' + money(sum(profits)) + '   |   تعداد فروش: ' + fa(sum(s['quantity'] for s in rows))
        if not rows:
            text += '   |   فروشی در این بازه ثبت نشده است.'
        if unknown:
            text += '\n' + fa(unknown) + ' ثبت فاقد اطلاعات محاسبه سود است و در مجموع سود لحاظ نشده.'
        total.setText(text)
        purchases = sorted((p for p in app.data.get('generalPurchases', []) if start <= p['date'] <= end), key=lambda p:p['date'])
        buy_table.setRowCount(len(purchases))
        for row, purchase in enumerate(purchases):
            values = [fa(jd(purchase['date'])), purchase['productName'], fa(purchase['quantity']), money(purchase['unitPrice']), money(purchase['quantity'] * purchase['unitPrice'])]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setToolTip(value)
                buy_table.setItem(row, column, item)
            buy_table.setRowHeight(row, 48)
        buy_total.setText('مجموع خرید: ' + money(sum(p['quantity'] * p['unitPrice'] for p in purchases)))

    def choose_day():
        import jdatetime
        calendar = Calendar(dialog)
        calendar.value = state['day']
        calendar.anchor = jdatetime.date.fromgregorian(date=date.fromisoformat(state['day'])).replace(day=1)
        calendar.draw()
        if calendar.exec() == calendar.Accepted:
            state['day'] = calendar.value
            refresh()

    def use_today():
        state['day'] = today()
        refresh()

    choose.clicked.connect(choose_day)
    current.clicked.connect(use_today)
    refresh()
    dialog.exec()
