# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'pymazon_qt.ui'
#
# Created: Sun Jan 31 18:31:12 2010
#      by: PyQt4 UI code generator 4.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(664, 482)
        self.centralwidget = QtGui.QWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.amz_button = QtGui.QPushButton(self.centralwidget)
        self.amz_button.setObjectName("amz_button")
        self.gridLayout_2.addWidget(self.amz_button, 0, 0, 1, 1)
        self.dir_button = QtGui.QPushButton(self.centralwidget)
        self.dir_button.setObjectName("dir_button")
        self.gridLayout_2.addWidget(self.dir_button, 1, 0, 1, 1)
        self.amz_lineedit = QtGui.QLineEdit(self.centralwidget)
        self.amz_lineedit.setReadOnly(True)
        self.amz_lineedit.setObjectName("amz_lineedit")
        self.gridLayout_2.addWidget(self.amz_lineedit, 0, 1, 1, 1)
        self.dir_lineedit = QtGui.QLineEdit(self.centralwidget)
        self.dir_lineedit.setReadOnly(True)
        self.dir_lineedit.setObjectName("dir_lineedit")
        self.gridLayout_2.addWidget(self.dir_lineedit, 1, 1, 1, 1)
        self.dl_button = QtGui.QPushButton(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dl_button.sizePolicy().hasHeightForWidth())
        self.dl_button.setSizePolicy(sizePolicy)
        self.dl_button.setObjectName("dl_button")
        self.gridLayout_2.addWidget(self.dl_button, 0, 2, 2, 1)
        self.tableView = QtGui.QTableView(self.centralwidget)
        self.tableView.setObjectName("tableView")
        self.gridLayout_2.addWidget(self.tableView, 2, 0, 1, 3)
        self.fmt_box = QtGui.QComboBox(self.centralwidget)
        self.fmt_box.setObjectName("fmt_box")
        self.gridLayout_2.addWidget(self.fmt_box, 3, 1, 1, 2)
        self.filename_label = QtGui.QLabel(self.centralwidget)
        self.filename_label.setObjectName("filename_label")
        self.gridLayout_2.addWidget(self.filename_label, 3, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.fmt_box.setCurrentIndex(-1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Pymazon", None, QtGui.QApplication.UnicodeUTF8))
        self.amz_button.setText(QtGui.QApplication.translate("MainWindow", "Load AMZ File", None, QtGui.QApplication.UnicodeUTF8))
        self.dir_button.setText(QtGui.QApplication.translate("MainWindow", "Save Directory", None, QtGui.QApplication.UnicodeUTF8))
        self.dl_button.setText(QtGui.QApplication.translate("MainWindow", "Download", None, QtGui.QApplication.UnicodeUTF8))
        self.filename_label.setText(QtGui.QApplication.translate("MainWindow", "Filename Format", None, QtGui.QApplication.UnicodeUTF8))

