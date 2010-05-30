# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '_qtgui.ui'
#
# Created: Thu Feb  4 20:13:54 2010
#      by: PyQt4 UI code generator 4.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(664, 481)
        self.centralwidget = QtGui.QWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.amz_button = QtGui.QPushButton(self.centralwidget)
        self.amz_button.setObjectName("amz_button")
        self.gridLayout.addWidget(self.amz_button, 0, 0, 1, 1)
        self.amz_lineedit = QtGui.QLineEdit(self.centralwidget)
        self.amz_lineedit.setReadOnly(True)
        self.amz_lineedit.setObjectName("amz_lineedit")
        self.gridLayout.addWidget(self.amz_lineedit, 0, 1, 1, 1)
        self.dl_button = QtGui.QPushButton(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dl_button.sizePolicy().hasHeightForWidth())
        self.dl_button.setSizePolicy(sizePolicy)
        self.dl_button.setObjectName("dl_button")
        self.gridLayout.addWidget(self.dl_button, 0, 2, 3, 1)
        self.dir_button = QtGui.QPushButton(self.centralwidget)
        self.dir_button.setObjectName("dir_button")
        self.gridLayout.addWidget(self.dir_button, 1, 0, 1, 1)
        self.dir_lineedit = QtGui.QLineEdit(self.centralwidget)
        self.dir_lineedit.setReadOnly(True)
        self.dir_lineedit.setObjectName("dir_lineedit")
        self.gridLayout.addWidget(self.dir_lineedit, 1, 1, 1, 1)
        self.filename_label = QtGui.QLabel(self.centralwidget)
        self.filename_label.setAlignment(QtCore.Qt.AlignCenter)
        self.filename_label.setObjectName("filename_label")
        self.gridLayout.addWidget(self.filename_label, 2, 0, 1, 1)
        self.fmt_box = QtGui.QComboBox(self.centralwidget)
        self.fmt_box.setObjectName("fmt_box")
        self.gridLayout.addWidget(self.fmt_box, 2, 1, 1, 1)
        self.tableView = QtGui.QTableView(self.centralwidget)
        self.tableView.setObjectName("tableView")
        self.gridLayout.addWidget(self.tableView, 3, 0, 1, 3)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.fmt_box.setCurrentIndex(-1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "Pymazon", None, QtGui.QApplication.UnicodeUTF8))
        self.amz_button.setText(QtGui.QApplication.translate("MainWindow", "Load AMZ File", None, QtGui.QApplication.UnicodeUTF8))
        self.dl_button.setText(QtGui.QApplication.translate("MainWindow", "Download", None, QtGui.QApplication.UnicodeUTF8))
        self.dir_button.setText(QtGui.QApplication.translate("MainWindow", "Save Directory", None, QtGui.QApplication.UnicodeUTF8))
        self.filename_label.setText(QtGui.QApplication.translate("MainWindow", "Name Format", None, QtGui.QApplication.UnicodeUTF8))

