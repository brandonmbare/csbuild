from PyQt4 import QtCore, QtGui
import os
import threading
import time
import math
import signal
from csbuild import _shared_globals

class MainWindow( QtGui.QMainWindow ):
	def __init__(self, *args, **kwargs):
		QtGui.QMainWindow.__init__(self, *args, **kwargs)
		
		self.setObjectName("MainWindow")
		
		self.resize(1024, 600)
		
		self.centralWidget = QtGui.QWidget(self)
		self.centralWidget.setObjectName("centralWidget")
		
		self.mainLayout = QtGui.QHBoxLayout(self.centralWidget)
		
		self.verticalLayout = QtGui.QVBoxLayout()
		self.verticalLayout.setObjectName("verticalLayout")
	
		self.m_buildSummaryLabel = QtGui.QLabel(self.centralWidget)
		self.m_buildSummaryLabel.setObjectName("m_buildSummaryLabel")
		font = QtGui.QFont()
		font.setPointSize( 16 )
		self.m_buildSummaryLabel.setFont(font)

		self.verticalLayout.addWidget(self.m_buildSummaryLabel)

		self.horizontalLayout = QtGui.QHBoxLayout()
		self.horizontalLayout.setObjectName("horizontalLayout")
		self.m_successfulBuildsLabel = QtGui.QLabel(self.centralWidget)
		self.m_successfulBuildsLabel.setObjectName("m_successfulBuildsLabel")

		self.horizontalLayout.addWidget(self.m_successfulBuildsLabel)

		self.m_failedBuildsLabel = QtGui.QLabel(self.centralWidget)
		self.m_failedBuildsLabel.setObjectName("m_failedBuildsLabel")

		self.horizontalLayout.addWidget(self.m_failedBuildsLabel)

		horizontalSpacer_2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

		self.horizontalLayout.addItem(horizontalSpacer_2)


		self.verticalLayout.addLayout(self.horizontalLayout)

		self.m_buildTree = QtGui.QTreeWidget(self.centralWidget)
		self.m_buildTree.setColumnCount(8)
		self.m_buildTree.setColumnWidth( 0, 25 )
		self.m_buildTree.setColumnWidth( 1, 250 )
		self.m_buildTree.setColumnWidth( 2, 100 )
		self.m_buildTree.setColumnWidth( 3, 125 )
		self.m_buildTree.setColumnWidth( 4, 75 )
		self.m_buildTree.setColumnWidth( 5, 165 )
		self.m_buildTree.setColumnWidth( 6, 165 )
		
		self.m_treeHeader = QtGui.QTreeWidgetItem()
		#self.m_treeHeader.setTextAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
		self.m_buildTree.setHeaderItem(self.m_treeHeader)
		
		self.m_buildTree.setObjectName("m_buildTree")
		self.m_buildTree.setAlternatingRowColors(True)
		self.m_buildTree.setUniformRowHeights(True)
		self.m_buildTree.setSortingEnabled(True)
		self.m_buildTree.setAnimated(True)
		#self.m_buildTree.header().setCascadingSectionResizes(True)
		self.m_buildTree.header().setStretchLastSection(True)
		self.m_buildTree.currentItemChanged.connect(self.SelectionChanged)
		self.m_buildTree.expanded.connect(self.ForceUpdateProjects)

		self.verticalLayout.addWidget(self.m_buildTree)

		self.m_mainProgressBar = QtGui.QProgressBar(self.centralWidget)
		self.m_mainProgressBar.setObjectName("m_mainProgressBar")
		self.m_mainProgressBar.setValue(0)

		self.verticalLayout.addWidget(self.m_mainProgressBar)

		self.horizontalLayout_2 = QtGui.QHBoxLayout()
		self.horizontalLayout_2.setObjectName("horizontalLayout_2")
		self.m_filesCompletedLabel = QtGui.QLabel(self.centralWidget)
		self.m_filesCompletedLabel.setObjectName("m_filesCompletedLabel")

		self.horizontalLayout_2.addWidget(self.m_filesCompletedLabel)

		horizontalSpacer = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)

		self.horizontalLayout_2.addItem(horizontalSpacer)

		self.m_timeLeftLabel = QtGui.QLabel(self.centralWidget)
		self.m_timeLeftLabel.setObjectName("m_timeLeftLabel")

		self.horizontalLayout_2.addWidget(self.m_timeLeftLabel)
		self.m_timeLeftLabel.hide()


		self.verticalLayout.addLayout(self.horizontalLayout_2)
		
		self.mainLayout.addLayout(self.verticalLayout)
		
		self.m_pushButton =  QtGui.QPushButton(self.centralWidget)
		self.m_pushButton.setObjectName("self.m_pushButton")
		sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
		sizePolicy.setHorizontalStretch(0)
		sizePolicy.setVerticalStretch(0)
		sizePolicy.setHeightForWidth(self.m_pushButton.sizePolicy().hasHeightForWidth())
		self.m_pushButton.setSizePolicy(sizePolicy)
		self.m_pushButton.setMaximumSize(QtCore.QSize(20, 16777215))
		self.m_pushButton.setCheckable(True)
		self.m_pushButton.toggled.connect(self.ButtonClicked)

		self.mainLayout.addWidget(self.m_pushButton)

		self.m_textEdit = QtGui.QTextEdit(self.centralWidget)
		self.m_textEdit.setObjectName("textEdit")
		self.m_textEdit.setReadOnly(True)
		self.m_textEdit.setFontFamily("monospace")
		self.m_textEdit.hide()

		self.mainLayout.addWidget(self.m_textEdit)

		self.setCentralWidget(self.centralWidget)

		self.retranslateUi()

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.onTick)
		self.timer.start(100)

		QtCore.QMetaObject.connectSlotsByName(self)

		self.readyToClose = False

		self.marqueeValue = 0
		self.marqueeInverted = True

		self.successfulBuilds = set()
		self.failedBuilds = set()

	def ButtonClicked(self, toggled):
		if toggled:
			self.m_textEdit.show()
		else:
			self.m_textEdit.hide()

	def SelectionChanged(self, current, previous):
		if current is None:
			outStr = ""
			for project in _shared_globals.sortedProjects:
				outStr += ("=" * 40) + "\n\n"
				outStr += project.name
				outStr += ("=" * 40) + "\n\n"
				for filename in project.compileOutput:
					outStr += filename
					errors = ""
					output = ""
					if filename in project.compileErrors:
						errors = project.compileErrors[filename]
					output = project.compileOutput[filename]
					if errors or output:
						outStr += "\n" + ("-" * len(filename)) + "\n\n"
						outStr += "\n" + ("-" * 40) + "\n\n"
						if errors:
							outStr += "ERROR OUTPUT:\n\n" + errors + "\n\n"
						if output:
							outStr += "OUTPUT:\n\n" + output + "\n\n"
				outStr += "\n\n"
			if outStr != self.m_textEdit.toPlainText():
				self.m_textEdit.setText(outStr)
		else:
			for project in _shared_globals.sortedProjects:
				widget = None
				for i in range(self.m_buildTree.topLevelItemCount()):
					tempWidget = self.m_buildTree.topLevelItem(i)
					name = tempWidget.text(3)
					target = tempWidget.text(4)
					if name == project.name and target == project.targetName:
						widget = tempWidget
						break
				if not widget:
					continue

				if widget == current:
					outStr = ""
					for filename in project.compileOutput:
						errors = ""
						output = ""
						if filename in project.compileErrors:
							errors = project.compileErrors[filename]
						output = project.compileOutput[filename]
						if errors or output:
							outStr += filename
							outStr += "\n" + ("=" * 40) + "\n\n"
							if errors:
								outStr += "ERROR OUTPUT:\n\n" + errors + "\n\n"
							if output:
								outStr += "OUTPUT:\n\n" + output + "\n\n"
					if outStr != self.m_textEdit.toPlainText():
						self.m_textEdit.setText(outStr)
				elif widget.isExpanded():
					def HandleChild( idx, file ):
						childWidget = widget.child(idx)

						if childWidget == current:
							outStr = ""
							errors = ""
							output = ""
							if file in project.compileErrors:
								errors = project.compileErrors[file]
							if file in project.compileOutput:
								output = project.compileOutput[file]
							if errors or output:
								outStr += file
								outStr += "\n" + ("=" * 40) + "\n\n"
								if errors:
									outStr += "ERROR OUTPUT:\n\n" + errors + "\n\n"
								if output:
									outStr += "OUTPUT:\n\n" + output + "\n\n"
							if outStr != self.m_textEdit.toPlainText():
								self.m_textEdit.setText(outStr)


					idx = 0
					if project.needs_cpp_precompile:
						HandleChild( idx, project.cppheaderfile )
						idx += 1

					if project.needs_c_precompile:
						HandleChild( idx, project.cheaderfile )
						idx += 1

					for file in project.final_chunk_set:
						HandleChild( idx, file )
						idx += 1

	def ForceUpdateProjects(self):
		self.UpdateProjects(True)

	def UpdateProjects(self, forceUpdate = False):
		updatedProjects = []

		for project in _shared_globals.sortedProjects:
			project.mutex.acquire()
			if project.updated or forceUpdate:
				updatedProjects.append(project)
				project.updated = False
			project.mutex.release()

		if not updatedProjects:
			return

		self.m_buildTree.setSortingEnabled(False)
		if self.marqueeValue == 100 or self.marqueeValue == 0:
			self.marqueeInverted = not self.marqueeInverted

		if self.marqueeInverted:
			self.marqueeValue -= 25
		else:
			self.marqueeValue += 25

		selectedWidget = self.m_buildTree.currentItem()

		for project in updatedProjects:
			widget = None
			for i in range(self.m_buildTree.topLevelItemCount()):
				tempWidget = self.m_buildTree.topLevelItem(i)
				name = tempWidget.text(3)
				target = tempWidget.text(4)
				if name == project.name and target == project.targetName:
					widget = tempWidget
					break
			if not widget:
				continue

			if selectedWidget == widget:
				self.SelectionChanged(selectedWidget, selectedWidget)


			def drawProgressBar( progressBar, widget, state, startTime, endTime, percent, forFile ):
				if(
					state >= _shared_globals.ProjectState.BUILDING and
					state != _shared_globals.ProjectState.FAILED
				):
					if not forFile or state != _shared_globals.ProjectState.BUILDING:
						progressBar.setValue( percent )
					progressBar.setFormat( "%p%" )
					widget.setText(1, "{0:03}".format(percent))

				if state == _shared_globals.ProjectState.BUILDING:
					widget.setText(2, "Building")
					if forFile:
						progressBar.setStyleSheet(
							"""
							QProgressBar::chunk
							{{
								background-color: #FFD800;
								width: {}px;
								margin: 0.5px;
							}}
							QProgressBar
							{{
								border: 1px solid black;
								border-radius: 3px;
								padding: 0px;
								text-align: center;
							}}
							""".format(float(progressBar.width()-1)/30.0)
						)

						#progressBar.setInvertedAppearance( self.marqueeInverted )
						#progressBar.setValue( self.marqueeValue )
						progressBar.setValue( 100 )

						progressBar.setTextVisible(False)
					else:
						progressBar.setStyleSheet(
							"""
							QProgressBar::chunk
							{
								background-color: #0040FF;
							}
							QProgressBar
							{
								border: 1px solid black;
								border-radius: 3px;
								padding: 0px;
								text-align: center;
							}
							"""
						)
						widget.setText(5, time.asctime(time.localtime(startTime)))
				if state == _shared_globals.ProjectState.WAITING_FOR_LINK:
					widget.setText(2,"Link pending...")
					progressBar.setStyleSheet(
						"""
						QProgressBar::chunk
						{
							background-color: #008080;
						}
						QProgressBar
						{
							border: 1px solid black;
							border-radius: 3px;
							background: #505050;
							padding: 0px;
							text-align: center;
						}
						"""
					)
				if state == _shared_globals.ProjectState.LINKING:
					widget.setText(2, "Linking")
					progressBar.setStyleSheet(
						"""
						QProgressBar::chunk
						{
							background-color: #00E060;
						}
						QProgressBar
						{
							border: 1px solid black;
							border-radius: 3px;
							background: #505050;
							padding: 0px;
							text-align: center;
							color: black;
						}
						"""
					)
				if state == _shared_globals.ProjectState.FINISHED:
					widget.setText(2, "Done!")
					progressBar.setStyleSheet(
						"""
						QProgressBar::chunk
						{
							background-color: #00FF80;
						}
						QProgressBar
						{
							border: 1px solid black;
							border-radius: 3px;
							background: #505050;
							padding: 0px;
							text-align: center;
							color: black;
						}
						"""
					)
					widget.setText(5, time.asctime(time.localtime(startTime)))
					widget.setText(6, time.asctime(time.localtime(endTime)))
					timeDiff = endTime - startTime
					minutes = math.floor( timeDiff / 60 )
					seconds = round( timeDiff % 60 )
					widget.setText(7, "{0:2}:{1:02}".format( int(minutes), int(seconds) ) )

				if state == _shared_globals.ProjectState.FAILED:
					widget.setText(2, "Build Failed!")
					progressBar.setStyleSheet(
						"""
						QProgressBar::chunk
						{
							background-color: #800000;
						}
						QProgressBar
						{
							border: 1px solid black;
							border-radius: 3px;
							background: #505050;
							padding: 0px;
							text-align: center;
						}
						"""
					)
					widget.setText(5, time.asctime(time.localtime(startTime)))
					widget.setText(6, time.asctime(time.localtime(endTime)))
					timeDiff = endTime - startTime
					minutes = math.floor( timeDiff / 60 )
					seconds = round( timeDiff % 60 )
					widget.setText(7, "{0:2}:{1:02}".format( int(minutes), int(seconds) ) )

			progressBar = self.m_buildTree.itemWidget(widget, 1)

			project.mutex.acquire( )
			complete = project.compiles_completed
			project.mutex.release( )

			total = len( project.final_chunk_set ) + int(
					project.needs_c_precompile ) + int(
					project.needs_cpp_precompile )
			percent = 100 if total == 0 else ( float(complete) / float(total) ) * 100
			if percent == 100 and project.state < _shared_globals.ProjectState.FINISHED:
				percent = 99

			drawProgressBar( progressBar, widget, project.state, project.startTime, project.endTime, percent, False )


			if project.state == _shared_globals.ProjectState.FINISHED:
				self.successfulBuilds.add(project.key)
			elif project.state == _shared_globals.ProjectState.FAILED:
				self.failedBuilds.add(project.key)

			if widget.isExpanded():
				def HandleChildProgressBar( idx, file ):
					childWidget = widget.child(idx)
					progressBar = self.m_buildTree.itemWidget(childWidget, 1)

					project.mutex.acquire( )
					try:
						state = project.fileStatus[file]
					except:
						state = _shared_globals.ProjectState.PENDING

					try:
						startTime = project.fileStart[file]
						endTime = project.fileEnd[file]
					except:
						startTime = 0
						endTime = 0

					project.mutex.release( )

					drawProgressBar( progressBar, childWidget, state, startTime, endTime, 0 if state <= _shared_globals.ProjectState.BUILDING else 100, True )

					if selectedWidget == childWidget:
						self.SelectionChanged(selectedWidget, selectedWidget)


				idx = 0
				if project.needs_cpp_precompile:
					HandleChildProgressBar( idx, project.cppheaderfile )
					idx += 1

				if project.needs_c_precompile:
					HandleChildProgressBar( idx, project.cheaderfile )
					idx += 1

				for file in project.final_chunk_set:
					HandleChildProgressBar( idx, file )
					idx += 1

		self.m_buildTree.setSortingEnabled(True)

		successcount = len(self.successfulBuilds)
		failcount = len(self.failedBuilds)

		self.m_successfulBuildsLabel.setText("Successful Builds: {}".format(successcount))
		self.m_failedBuildsLabel.setText("Failed Builds: {}".format(failcount))

		if successcount + failcount == len(_shared_globals.sortedProjects):
			self.readyToClose = True
			if _shared_globals.autoCloseGui:
				self.close()


	def retranslateUi(self):
		self.setWindowTitle("MainWindow")
		self.m_buildSummaryLabel.setText("Build Started at 00:00... (00:00)")
		self.m_successfulBuildsLabel.setText("Successful Builds: 0")
		self.m_failedBuildsLabel.setText("Failed Builds: 0")
		self.m_treeHeader.setText(0, "#")
		self.m_treeHeader.setText(1, "Progress")
		self.m_treeHeader.setText(2, "Status")
		self.m_treeHeader.setText(3, "Name")
		self.m_treeHeader.setText(4, "Target")
		self.m_treeHeader.setText(5, "Build Started")
		self.m_treeHeader.setText(6, "Build Finished")
		self.m_treeHeader.setText(7, "Time")
		self.m_buildTree.setColumnWidth( 0, 50 )
		self.m_buildTree.setColumnWidth( 1, 250 )
		self.m_buildTree.setColumnWidth( 2, 100 )
		self.m_buildTree.setColumnWidth( 3, 125 )
		self.m_buildTree.setColumnWidth( 4, 75 )
		self.m_buildTree.setColumnWidth( 5, 165 )
		self.m_buildTree.setColumnWidth( 6, 165 )
		self.m_buildTree.setColumnWidth( 7, 50 )

		self.m_filesCompletedLabel.setText("0/0 files compiled")
		self.m_timeLeftLabel.setText("Est. Time Left: 0:00")
		self.m_pushButton.setText(">")

	def onTick(self):
		self.UpdateProjects()

		totalCompletedCompiles = 0
		for project in _shared_globals.sortedProjects:
			totalCompletedCompiles += project.compiles_completed

		perc = 100 if _shared_globals.total_compiles == 0 else float(totalCompletedCompiles)/float(_shared_globals.total_compiles) * 100
		if perc == 100 and not self.readyToClose:
			perc = 99

		self.m_mainProgressBar.setValue( perc )
		self.m_filesCompletedLabel.setText("{}/{} files compiled".format(totalCompletedCompiles, _shared_globals.total_compiles))

		curtime = time.time( )
		timeDiff = curtime - _shared_globals.starttime
		minutes = math.floor( timeDiff / 60 )
		seconds = round( timeDiff % 60 )

		self.m_buildSummaryLabel.setText("Build Started {0}... ({1}:{2:02})".format( time.asctime(time.localtime(_shared_globals.starttime)), int(minutes), int(seconds) ))

		if _shared_globals.times and _shared_globals.lastupdate >= 0:

			avgtime = sum( _shared_globals.times ) / (len( _shared_globals.times ))
			top = _shared_globals.lastupdate + ((avgtime * (_shared_globals.total_compiles -
															len(
																_shared_globals.times ))) / _shared_globals
												.max_threads)

			diff = max( top - timeDiff, 0 )
			estmin = max( math.floor( diff / 60 ), 0 )
			estsec = max( round( diff % 60 ), 0 )

			self.m_timeLeftLabel.setText("Est. Time Left: {0:2}:{1:02}".format( int(estmin), int(estsec) ))
		else:
			self.m_timeLeftLabel.setText("Est. Time Left: Unknown")

		if self.readyToClose:
			self.timer.stop()

	def closeEvent(self, event):
		if not self.readyToClose:
			answer = QtGui.QMessageBox.question(
				self,
				"Really close?",
				"A compile is still in progress. Closing will cancel it. Are you sure you want to close?",
				QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
				QtGui.QMessageBox.No
			)
			if answer == QtGui.QMessageBox.Yes:
				QtGui.QMainWindow.closeEvent(self, event)
				os.kill(os.getpid(), signal.SIGINT)
			else:
				event.ignore()
		else:
			QtGui.QMainWindow.closeEvent(self, event)



class GuiThread( threading.Thread ):
	"""Multithreaded build system, launches a new thread to run the compiler in.
	Uses a threading.BoundedSemaphore object to keep the number of threads equal to the number of processors on the
	machine.
	"""


	def __init__( self ):
		"""Initialize the object. Also handles above-mentioned bug with dummy threads."""
		threading.Thread.__init__( self )
		self.app = None
		#Prevent certain versions of python from choking on dummy threads.
		if not hasattr( threading.Thread, "_Thread__block" ):
			threading.Thread._Thread__block = _shared_globals.dummy_block( )


	def run( self ):
		self.app = QtGui.QApplication([])
		window = MainWindow()

		window.m_buildTree.setSortingEnabled(False)
		row = 0
		for project in _shared_globals.sortedProjects:
			row += 1
			widgetItem = QtGui.QTreeWidgetItem()
			window.m_buildTree.addTopLevelItem(widgetItem)
			widgetItem.setText(0, str(row))
			widgetItem.setText(2, "Pending...")
			widgetItem.setText(3, project.name)
			widgetItem.setText(4, project.targetName)

			def AddProgressBar( widgetItem ):
				progressBar = QtGui.QProgressBar()

				progressBar.setStyleSheet(
					"""
					QProgressBar::chunk
					{
						background-color: #808080;
					}
					QProgressBar
					{
						border: 1px solid black;
						border-radius: 3px;
						padding: 0px;
						text-align: center;
					}
					"""
				)

				progressBar.setFormat("Pending...")
				progressBar.setValue(100)
				window.m_buildTree.setItemWidget( widgetItem, 1, progressBar )

			AddProgressBar( widgetItem )

			idx = 0
			if project.needs_cpp_precompile:
				idx += 1
				childItem = QtGui.QTreeWidgetItem( widgetItem )
				childItem.setText(0, "{}.{}".format(row, idx))
				childItem.setText(2, "Pending...")
				childItem.setText(3, os.path.basename(project.cppheaderfile))
				childItem.setText(4, project.targetName)
				AddProgressBar( childItem )

				widgetItem.addChild(childItem)

				for header in project.cpppchcontents:
					subChildItem = QtGui.QTreeWidgetItem( childItem )
					subChildItem.setText( 1, os.path.basename(header) )
					childItem.addChild(subChildItem)

			if project.needs_c_precompile:
				idx += 1
				childItem = QtGui.QTreeWidgetItem( widgetItem )
				childItem.setText(0, "{}.{}".format(row, idx))
				childItem.setText(2, "Pending...")
				childItem.setText(3, os.path.basename(project.cheaderfile))
				childItem.setText(4, project.targetName)
				AddProgressBar( childItem )

				widgetItem.addChild(childItem)

				for header in project.cpchcontents:
					subChildItem = QtGui.QTreeWidgetItem( childItem )
					subChildItem.setText( 1, os.path.basename(header) )
					childItem.addChild(subChildItem)

			for source in project.final_chunk_set:
				idx += 1
				childItem = QtGui.QTreeWidgetItem( widgetItem )
				childItem.setText(0, "{}.{}".format(row, idx))
				childItem.setText(2, "Pending...")
				childItem.setText(3, os.path.basename(source))
				childItem.setText(4, project.targetName)

				AddProgressBar( childItem )

				widgetItem.addChild(childItem)

				if source in project.chunksByFile:
					for piece in project.chunksByFile[source]:
						subChildItem = QtGui.QTreeWidgetItem( childItem )
						subChildItem.setText( 1, piece )
						childItem.addChild(subChildItem)

		window.m_buildTree.setSortingEnabled(True)

		window.show()
		self.app.exec_()

	def stop(self):
		if self.app():
			self.app.quit()

_thread = None

def run():
	global _thread
	_thread = GuiThread()
	_thread.start()

def stop():
	global _thread
	if _thread:
		_thread.stop()