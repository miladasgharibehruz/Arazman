"""Daily and Jalali monthly sales reporting, using recorded sale snapshots."""
from datetime import date


def report_sales(data, start, end):
    return sorted((s for s in data.get('sales', [])
                   if not s.get('cancelled') and start <= s['date'] <= end),
                  key=lambda s: (s['date'], s.get('productName', '')))


def jalali_range(day, mode):
    import jdatetime
    selected = jdatetime.date.fromgregorian(date=date.fromisoformat(day))
    if mode == 'year':
        first=jdatetime.date(selected.year,1,1)
        last=jdatetime.date(selected.year,12,30 if first.isleap() else 29)
        return first.togregorian().isoformat(),last.togregorian().isoformat()
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
                                   QTabWidget, QFormLayout, QLineEdit, QSpinBox, QAbstractSpinBox, QDialog)
    dialog, layout = app.dialog('گزارش کلی')
    dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dialog.resize(1160, 650)
    import jdatetime
    state = {'day': today(), 'mode': 'day'}
    year = QSpinBox()
    year.setRange(1300, 1600)
    year.setValue(jdatetime.date.today().year)
    year.setButtonSymbols(QAbstractSpinBox.NoButtons)
    year.setPrefix('سال ')
    year.hide()
    top = QHBoxLayout()
    layout.addLayout(top)
    choose = QPushButton()
    top.addWidget(choose)
    current = QPushButton('امروز')
    top.addWidget(current)
    top.addWidget(year)
    top.addStretch()
    filters = QHBoxLayout()
    layout.addLayout(filters)
    group = QButtonGroup(dialog)
    group.setExclusive(True)
    for mode, label in [('day', 'روز انتخاب‌شده'), ('month', 'کل ماه'),
                        ('first', '۱ تا ۱۵ ماه'), ('second', '۱۵ تا پایان ماه'), ('year', 'سال '+fa(jdatetime.date.today().year))]:
        button = QPushButton(label)
        button.setCheckable(True)
        button.setChecked(mode == 'day')
        if mode == 'year':year_button = button
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
    table.setHorizontalHeaderLabels(['تاریخ', 'نام کالا', 'نحوه فروش', 'تعداد',
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
    stats_row = QHBoxLayout()
    sales_layout.addLayout(stats_row)
    stat_values = []
    dark = app.data.get('theme') in ['سرمه‌ای و مسی','تیره و نئونی']
    colors = [('#193b30','#a0efbe'),('#17334b','#a6d8ff'),('#352748','#dcc0ff'),('#40321d','#ffe0a3')] if dark else [('#e9f8ee','#247642'),('#eaf3ff','#245c97'),('#f3ecfb','#7952a3'),('#fff5e4','#946b22')]
    for caption, (background, foreground) in zip(['مجموع سود','مجموع فروش','تعداد فروخته‌شده','تعداد ثبت فروش'],colors):
        card = QWidget()
        card.setStyleSheet('QWidget{background:'+background+';border-radius:12px;} QLabel{background:transparent;color:'+foreground+';}')
        card_layout = QVBoxLayout(card)
        heading = QLabel(caption)
        heading.setAlignment(Qt.AlignCenter)
        value = QLabel()
        value.setAlignment(Qt.AlignCenter)
        value.setStyleSheet('font-size:17px;font-weight:bold;padding:8px;')
        card_layout.addWidget(heading)
        card_layout.addWidget(value)
        stat_values.append(value)
        stats_row.addWidget(card,1)
    sales_layout.addWidget(total)
    total.setStyleSheet('font-size:12px;padding:3px;')
    CHANNELS = {'digikala':'دیجیکالا','arazman':'آرازمان','basalam':'باسلام','snappshop':'اسنپ شاپ','inperson':'حضوری','instagram':'اینستاگرام','rubika':'روبیکا','telegram':'تلگرام','bale':'بله'}
    def rounded(value):
        import math
        return math.floor(value + .5)
    buy_page = QWidget()
    buy_layout = QVBoxLayout(buy_page)
    tabs.addTab(buy_page, 'خرید')
    from inventory_ui import purchase_panel, sale_channel, make_copyable
    api = app.inventory_api
    purchase_refresh = purchase_panel(app, api, buy_layout)

    def refresh():
        choose.setText('انتخاب تاریخ: ' + fa(jd(state['day'])))
        choose.setVisible(state['mode']=='day')
        current.setVisible(state['mode']=='day')
        year.setVisible(state['mode']=='year')
        filter_day = jdatetime.date(year.value(),1,1).togregorian().isoformat() if state['mode']=='year' else state['day']
        start, end = jalali_range(filter_day, state['mode'])
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
                      sale_channel(sale, api), fa(quantity),
                      money(sale.get('purchasePriceAtSale')), money(sale['unitPrice']),
                      money(rounded(profit / quantity) if profit is not None and quantity else None),
                      money(profit), money(sale['totalPrice'])]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                item.setToolTip(value)
                table.removeCellWidget(row, column)
                table.setItem(row, column, item)
            table.setRowHeight(row, 60)
        make_copyable(table)
        for widget,value in zip(stat_values,[money(sum(profits)),money(sum(s['totalPrice'] for s in rows)),fa(sum(s['quantity'] for s in rows))+' عدد',fa(len(rows))]):
            widget.setText(value)
        text = 'فروشی در این بازه ثبت نشده است.' if not rows else ''
        if unknown:
            text += '\n' + fa(unknown) + ' ثبت فاقد اطلاعات محاسبه سود است و در مجموع سود لحاظ نشده.'
        total.setText(text)
        total.setVisible(bool(text))
        purchase_refresh(start, end)

    def choose_day():
        import jdatetime
        calendar = Calendar(dialog)
        calendar.value = state['day']
        calendar.anchor = jdatetime.date.fromgregorian(date=date.fromisoformat(state['day'])).replace(day=1)
        def select_date(selected):
            calendar.value = selected.togregorian().isoformat()
            calendar.accept()
        calendar.choose = select_date
        calendar.draw()
        if calendar.exec() == QDialog.Accepted:
            state['day'] = calendar.value
            refresh()

    def use_today():
        state['day'] = today()
        refresh()

    def year_changed(value):
        year_button.setText('سال '+fa(value))
        refresh()
    year.valueChanged.connect(year_changed)
    choose.clicked.connect(choose_day)
    current.clicked.connect(use_today)
    refresh()
    dialog.exec()
