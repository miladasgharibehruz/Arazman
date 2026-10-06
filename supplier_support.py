"""Supplier directory and product links for Arazman."""
import uuid


def get_supplier(data, supplier_id):
    return next((s for s in data.get('suppliers', []) if s['id'] == supplier_id), None)


def save_supplier(data, name, phone, address, supplier_id=None):
    name = name.strip()
    if not name:
        raise ValueError('نام مرجع الزامی است.')
    entries = data.setdefault('suppliers', [])
    supplier = get_supplier(data, supplier_id) if supplier_id else None
    if supplier_id and supplier is None:
        raise ValueError('مرجع انتخاب‌شده دیگر وجود ندارد.')
    if supplier is None:
        supplier = {'id': str(uuid.uuid4())}
        entries.append(supplier)
    supplier.update(name=name, phone=phone.strip(), address=address.strip())
    return supplier


def remove_supplier(data, supplier_id):
    supplier = get_supplier(data, supplier_id)
    if supplier is None:
        return
    data['suppliers'].remove(supplier)
    for product in data.get('active', []) + data.get('deleted', []):
        if product.get('supplierId') == supplier_id:
            product.pop('supplierId', None)


def supplier_details(supplier):
    if not supplier:
        return 'مرجعی انتخاب نشده است.'
    return '\n'.join([supplier['name'], 'شماره تماس: ' + (supplier.get('phone') or '—'),
                      'آدرس: ' + (supplier.get('address') or '—')])


def _window(app, title, width=760, height=560):
    from PySide6.QtCore import Qt
    dialog, layout = app.dialog(title)
    dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dialog.resize(width, height)
    return dialog, layout


def _directory(app, layout):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QLabel
    search = QLineEdit()
    search.setPlaceholderText('جستجو بین مراجع')
    listing = QListWidget()
    listing.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    details = QLabel('یک مرجع را انتخاب کنید.')
    details.setWordWrap(True)
    details.setTextFormat(Qt.PlainText)
    layout.addWidget(search)
    layout.addWidget(listing, 1)
    layout.addWidget(details)

    def refresh(selected=None):
        listing.clear()
        query = search.text().strip().casefold()
        for supplier in app.data.get('suppliers', []):
            if query and query not in supplier['name'].casefold():
                continue
            item = QListWidgetItem(supplier['name'])
            item.setData(Qt.UserRole, supplier['id'])
            item.setToolTip(supplier_details(supplier))
            listing.addItem(item)
            if supplier['id'] == selected:
                listing.setCurrentItem(item)
        if not listing.count():
            details.setText('مرجعی پیدا نشد.' if query else 'هنوز مرجعی ثبت نشده است.')

    def current():
        item = listing.currentItem()
        return get_supplier(app.data, item.data(Qt.UserRole)) if item else None

    listing.currentItemChanged.connect(lambda *_: details.setText(supplier_details(current())))
    search.textChanged.connect(lambda _: refresh())
    refresh()
    return listing, refresh, current


def choose_supplier(app, product):
    from PySide6.QtWidgets import QPushButton
    dialog, layout = _window(app, 'انتخاب مرجع برای '+product['name'], 640, 440)
    listing, refresh, current = _directory(app, layout)
    refresh(product.get('supplierId'))
    confirm = QPushButton('ثبت مرجع کالا')
    layout.addWidget(confirm)
    confirm.setEnabled(bool(current()))
    listing.currentItemChanged.connect(lambda *_: confirm.setEnabled(bool(current())))

    def commit():
        supplier = current()
        if supplier is None:
            return
        previous = get_supplier(app.data, product.get('supplierId'))
        product['supplierId'] = supplier['id']
        app.history(product, 'تغییر مرجع', previous['name'] if previous else None, supplier['name'])
        app.persist()
        app.render()
        dialog.accept()

    confirm.clicked.connect(commit)
    dialog.exec()


def manage_suppliers(app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QTabWidget, QLineEdit,
                                   QTextEdit, QPushButton, QLabel, QHBoxLayout, QMessageBox)
    dialog, layout = _window(app, 'مرجع')
    tabs = QTabWidget()
    tabs.setObjectName('settingsTabs')
    layout.addWidget(tabs)
    mine = QWidget()
    mine_layout = QVBoxLayout(mine)
    mine_listing, mine_refresh, mine_current = _directory(app, mine_layout)
    tabs.addTab(mine, 'مرجع من')

    def fields(parent_layout):
        form = QFormLayout()
        parent_layout.addLayout(form)
        name, phone, address = QLineEdit(), QLineEdit(), QTextEdit()
        phone.setLayoutDirection(Qt.LeftToRight)
        phone.setPlaceholderText('مثلاً 09123456789')
        address.setAcceptRichText(False)
        address.setMaximumHeight(110)
        form.addRow('نام مرجع', name)
        form.addRow('شماره تماس', phone)
        form.addRow('آدرس', address)
        return name, phone, address

    add_page = QWidget()
    add_layout = QVBoxLayout(add_page)
    add_name, add_phone, add_address = fields(add_layout)
    add_notice = QLabel()
    add_notice.setWordWrap(True)
    add_layout.addWidget(add_notice)
    add_button = QPushButton('ثبت مرجع')
    add_layout.addWidget(add_button)
    add_layout.addStretch()
    tabs.addTab(add_page, 'افزودن مرجع')

    edit_page = QWidget()
    edit_layout = QVBoxLayout(edit_page)
    edit_listing, edit_refresh, edit_current = _directory(app, edit_layout)
    edit_name, edit_phone, edit_address = fields(edit_layout)
    edit_notice = QLabel()
    edit_layout.addWidget(edit_notice)
    actions = QHBoxLayout()
    edit_layout.addLayout(actions)
    edit_button, delete_button = QPushButton('ثبت ویرایش'), QPushButton('حذف مرجع')
    actions.addWidget(edit_button)
    actions.addWidget(delete_button)
    tabs.addTab(edit_page, 'ویرایش یا حذف مرجع')

    def selection(*_):
        supplier = edit_current()
        for widget in [edit_name, edit_phone, edit_address, edit_button, delete_button]:
            widget.setEnabled(supplier is not None)
        edit_name.setText(supplier['name'] if supplier else '')
        edit_phone.setText(supplier.get('phone', '') if supplier else '')
        edit_address.setPlainText(supplier.get('address', '') if supplier else '')
        edit_notice.clear()

    edit_listing.currentItemChanged.connect(selection)
    selection()

    def add():
        try:
            supplier = save_supplier(app.data, add_name.text(), add_phone.text(), add_address.toPlainText())
        except ValueError as error:
            add_notice.setText(str(error))
            return
        app.persist()
        mine_refresh(supplier['id'])
        edit_refresh(supplier['id'])
        add_name.clear()
        add_phone.clear()
        add_address.clear()
        add_notice.setText('مرجع ثبت شد.')
        tabs.setCurrentIndex(0)

    def edit():
        supplier = edit_current()
        if supplier is None:
            return
        try:
            save_supplier(app.data, edit_name.text(), edit_phone.text(), edit_address.toPlainText(), supplier['id'])
        except ValueError as error:
            edit_notice.setText(str(error))
            return
        app.persist()
        app.render()
        mine_refresh(supplier['id'])
        edit_refresh(supplier['id'])
        edit_notice.setText('اطلاعات مرجع تغییر کرد.')

    def delete():
        supplier = edit_current()
        if supplier is None:
            return
        if QMessageBox.question(dialog, 'حذف مرجع', 'مرجع «'+supplier['name']+'» حذف شود؟ اتصال آن به کالاها نیز برداشته می‌شود.', QMessageBox.Yes|QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        remove_supplier(app.data, supplier['id'])
        app.persist()
        app.render()
        mine_refresh()
        edit_refresh()
        selection()

    add_button.clicked.connect(add)
    edit_button.clicked.connect(edit)
    delete_button.clicked.connect(delete)
    dialog.exec()
