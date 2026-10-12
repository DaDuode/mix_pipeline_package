import os
import time
import traceback
import re
from PySide2 import QtWidgets, QtCore, QtGui
import maya.cmds as cmds
import maya.mel as mel
import pymel.core as pmel

# ===================== FBX导出核心功能 =====================
def __publish_fbx(node, publish_path,start, end):
    """导出FBX文件的核心函数"""
    cmdstr = """
    FBXProperty Export|IncludeGrp|Geometry|SmoothingGroups -v true;
    FBXProperty Export|IncludeGrp|Animation -v true;
    FBXProperty Export|IncludeGrp|Animation|BakeComplexAnimation -v true;
    FBXProperty Export|IncludeGrp|Animation|BakeComplexAnimation|BakeFrameStart -v {start_f};
    FBXProperty Export|IncludeGrp|Animation|BakeComplexAnimation|BakeFrameEnd -v {end_f};
    FBXProperty Export|IncludeGrp|Animation|Deformation -v true;  
    FBXProperty Export|IncludeGrp|Animation|Deformation|Skins -v true;   
    FBXProperty Export|IncludeGrp|Animation|Deformation|Shape -v true;   
    FBXProperty Export|IncludeGrp|Animation|ConstraintsGrp|Constraint -v true;
    FBXProperty Export|IncludeGrp|Animation|ConstraintsGrp|Character -v true;
    FBXProperty Export|IncludeGrp|CameraGrp|Camera -v true;
    FBXProperty Export|AdvOptGrp|AxisConvGrp|UpAxis -v "Y";
    """
    cmdstr = cmdstr.format(start_f=start, end_f=end)
    mel.eval(cmdstr)
    pmel.select(cl=1)
    pmel.select(node)
    os.makedirs(os.path.dirname(publish_path), exist_ok=True)
    cmds.file(publish_path, force=1, options="v=0;", typ="FBX export", pr=1, es=1)

def game_export(node, publish_path, start, end):
    """游戏专用的FBX导出函数"""
    name = os.path.basename(publish_path).split('.')[0]
    pmel.select(cl=1)
    pmel.select(node)
    os.makedirs(os.path.dirname(publish_path), exist_ok=True)
    ppath = os.environ['MAYA_LOCATION']
    ppath = ppath+ "/plug-ins/fbx/plug-ins/FBX/Presets/export/Autodesk_ME_AnimationClipsGame.gamefbxexportpreset"
    cmdstr = """
    FBXPushSettings;
    FBXLoadExportPresetFile -f "{ppath}";
    FBXExportBakeComplexAnimation -v true;
    FBXExportBakeComplexStart -v {start_f};
    FBXExportBakeComplexEnd -v {end_f};
    FBXExportUpAxis "y";
    FBXExportSplitAnimationIntoTakes -v {name} {start_f} {end_f};
    FBXExportDeleteOriginalTakeOnSplitAnimation -v true;
    FBXExport -s -file "{publish_path}";
    FBXExportSplitAnimationIntoTakes -clear;
    FBXPopSettings;
    """
    cmdstr = cmdstr.format(ppath = ppath,name = name,start_f=str(start), end_f=str(end),publish_path = publish_path)
    print(cmdstr)
    mel.eval(cmdstr)
def core_run(file_path, shot_name, start, end,output_folder):
    """处理Maya文件的核心函数"""
    print(f"处理文件: {file_path}")
    cmds.file(new=True, force=1)
    cmds.file(file_path, open=True, force=True, loadAllReferences=True)
    root_path = os.path.dirname(file_path)

    if start == 1-8:
        # 检测到未输入起始帧 进行读取
        start = int(cmds.playbackOptions(q=True, min=True))-8
    if end == 24+8:
        # 检测到未输入结束帧 进行读取
        end = int(cmds.playbackOptions(q=True, max=True))+8
    print(f"处理 帧范围: {start} - {end}")
    # 处理相机
    cam_reg = "final_camera"
    cam_list = pmel.ls(type='camera')
    for cam in cam_list:
        if re.search(cam_reg, cam.getParent().name().lower()):
            camera_fbx = os.path.join(output_folder, shot_name, cam.getParent().name() + ".fbx").replace('\\', '/')
            __publish_fbx(cam.getParent().name(),camera_fbx, start, end )
   
    for ref in pmel.listReferences(loaded=1):
        ref_namespace = ref.namespace
        _model_mesh = f"|{ref_namespace}:model"
        root = f"|{ref_namespace}:root"
        
        if pmel.objExists(_model_mesh) and pmel.objExists(root):
            out_path = f"{output_folder}/{shot_name}/{shot_name}_{ref_namespace}.fbx"
            game_export([_model_mesh, root], out_path, start, end)
            print(f"导出: {out_path}")
        else:
            print(f"错误: {_model_mesh} 或 {root} 不存在，跳过...")

# ===================== 用户界面 =====================
class FolderSelectorUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(FolderSelectorUI, self).__init__(parent)
        self.setWindowTitle(u"Maya批量FBX导出工具")
        self.setMinimumSize(1000, 700)
        self.setup_ui()
        
        # 加载必要的插件
        for plugin in ["gameFbxExporter.mll", "fbxmaya.mll"]:
            if not cmds.pluginInfo(plugin, q=1, l=1):
                cmds.loadPlugin(plugin)
        mel.eval('optionVar -iv "SafeModeGlobalPy" 1;')
        mel.eval('optionVar -iv "SafeModeBuiltInCheck" 0;')
        mel.eval('optionVar -iv "SafeModeImportOption" 0;')
    def setup_ui(self):
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # ================= 文件夹选择部分 =================
        folder_group = QtWidgets.QGroupBox(u"文件夹设置")
        folder_layout = QtWidgets.QGridLayout(folder_group)
        
        # 输入文件夹
        folder_layout.addWidget(QtWidgets.QLabel(u"输入文件夹:"), 0, 0)
        self.folder1_lineedit = QtWidgets.QLineEdit()
        self.folder1_lineedit.setPlaceholderText(u"选择包含Maya文件的文件夹 (.ma/.mb)")
        folder1_btn = QtWidgets.QPushButton(u"浏览...")
        folder1_btn.clicked.connect(lambda: self.select_folder(self.folder1_lineedit))
        folder_layout.addWidget(self.folder1_lineedit, 0, 1)
        folder_layout.addWidget(folder1_btn, 0, 2)
        
        # 输出文件夹
        folder_layout.addWidget(QtWidgets.QLabel(u"输出文件夹:"), 1, 0)
        self.folder2_lineedit = QtWidgets.QLineEdit()
        self.folder2_lineedit.setPlaceholderText(u"选择FBX输出文件夹")
        folder2_btn = QtWidgets.QPushButton(u"浏览...")
        folder2_btn.clicked.connect(lambda: self.select_folder(self.folder2_lineedit))
        folder_layout.addWidget(self.folder2_lineedit, 1, 1)
        folder_layout.addWidget(folder2_btn, 1, 2)
        
        # 扫描按钮
        scan_btn = QtWidgets.QPushButton(u"扫描Maya文件")
        scan_btn.setFixedHeight(40)
        scan_btn.clicked.connect(self.scan_maya_files)
        folder_layout.addWidget(scan_btn, 0, 3, 2, 1)
        
        # ================= 帧范围设置部分 =================
        frame_group = QtWidgets.QGroupBox(u"帧范围设置")
        frame_layout = QtWidgets.QGridLayout(frame_group)
        
        # 全局设置
        frame_layout.addWidget(QtWidgets.QLabel(u"全局帧范围:"), 0, 0)
        
        # 开始帧
        start_frame_layout = QtWidgets.QHBoxLayout()
        start_frame_label = QtWidgets.QLabel(u"开始帧:")
        self.start_frame_spin = QtWidgets.QSpinBox()
        self.start_frame_spin.setRange(0, 999999)
        self.start_frame_spin.setValue(1)
        start_frame_layout.addWidget(start_frame_label)
        start_frame_layout.addWidget(self.start_frame_spin)
        frame_layout.addLayout(start_frame_layout, 0, 1)
        
        # 结束帧
        end_frame_layout = QtWidgets.QHBoxLayout()
        end_frame_label = QtWidgets.QLabel(u"结束帧:")
        self.end_frame_spin = QtWidgets.QSpinBox()
        self.end_frame_spin.setRange(1, 999999)
        self.end_frame_spin.setValue(24)
        end_frame_layout.addWidget(end_frame_label)
        end_frame_layout.addWidget(self.end_frame_spin)
        frame_layout.addLayout(end_frame_layout, 0, 2)
        
        # 应用按钮
        apply_global_btn = QtWidgets.QPushButton(u"应用到所有文件")
        apply_global_btn.clicked.connect(self.apply_global_frame_range)
        frame_layout.addWidget(apply_global_btn, 0, 3)
        
        # 文件设置
        frame_layout.addWidget(QtWidgets.QLabel(u"文件帧范围:"), 1, 0)
        
        # 文件开始帧
        file_start_frame_layout = QtWidgets.QHBoxLayout()
        file_start_frame_label = QtWidgets.QLabel(u"开始帧:")
        self.file_start_frame_spin = QtWidgets.QSpinBox()
        self.file_start_frame_spin.setRange(0, 999999)
        self.file_start_frame_spin.setValue(1)
        file_start_frame_layout.addWidget(file_start_frame_label)
        file_start_frame_layout.addWidget(self.file_start_frame_spin)
        frame_layout.addLayout(file_start_frame_layout, 1, 1)
        
        # 文件结束帧
        file_end_frame_layout = QtWidgets.QHBoxLayout()
        file_end_frame_label = QtWidgets.QLabel(u"结束帧:")
        self.file_end_frame_spin = QtWidgets.QSpinBox()
        self.file_end_frame_spin.setRange(1, 999999)
        self.file_end_frame_spin.setValue(24)
        file_end_frame_layout.addWidget(file_end_frame_label)
        file_end_frame_layout.addWidget(self.file_end_frame_spin)
        frame_layout.addLayout(file_end_frame_layout, 1, 2)
        
        # 应用按钮
        apply_selected_btn = QtWidgets.QPushButton(u"应用到选中文件")
        apply_selected_btn.clicked.connect(self.apply_selected_frame_range)
        frame_layout.addWidget(apply_selected_btn, 1, 3)
        
        # ================= 文件列表部分 =================
        table_group = QtWidgets.QGroupBox(u"Maya文件列表")
        table_layout = QtWidgets.QVBoxLayout(table_group)
        
        # 表格设置
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            u"选择", u"文件名", u"路径", u"大小 (KB)", u"镜头号", 
            u"开始帧", u"结束帧", u"状态"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.SelectedClicked)
        
        # 添加右键菜单
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 连接双击事件
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        
        table_layout.addWidget(self.table)
        
        # ================= 底部按钮 =================
        btn_layout = QtWidgets.QHBoxLayout()
        
        # 处理按钮
        process_btn = QtWidgets.QPushButton(u"处理选中文件")
        process_btn.setMinimumHeight(45)
        process_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        process_btn.clicked.connect(self.process_selected_files)
        
        # 刷新按钮
        refresh_btn = QtWidgets.QPushButton(u"刷新列表")
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.scan_maya_files)
        
        btn_layout.addWidget(process_btn)
        btn_layout.addWidget(refresh_btn)
        
        # 添加到主布局
        main_layout.addWidget(folder_group)
        main_layout.addWidget(frame_group)
        main_layout.addWidget(table_group)
        main_layout.addLayout(btn_layout)
    
    # ===================== 功能方法 =====================
    def select_folder(self, lineedit):
        """打开文件夹选择对话框"""
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, u"选择文件夹")
        if folder_path:
            lineedit.setText(folder_path)
    
    def scan_maya_files(self):
        """扫描文件夹中的Maya文件"""
        folder_path = self.folder1_lineedit.text()
        
        if not folder_path:
            cmds.warning(u"请先选择包含Maya文件的文件夹！")
            return
        
        if not os.path.exists(folder_path):             
            cmds.warning(u"文件夹路径无效，请重新选择！")
            return
        
        # 清空表格
        self.table.setRowCount(0)
        
        # 扫描文件
        maya_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.ma', '.mb')):
                    file_path = os.path.join(root, file).replace('\\', '/')
                    file_size = os.path.getsize(file_path) / 1024  # KB
                    basename = os.path.basename(file_path).split('.')[0]
                    # shot_name = '_'.join(basename.split('_')[:2])  # 提取镜头号
                    try:
                        shot_name =basename.split('_')[0]+'_'+basename.split('_')[1]
                    except:
                        shot_name = 'unknow'
                    maya_files.append((file, file_path, file_size, shot_name))
        
        if not maya_files:
            cmds.warning(u"未找到任何.ma或.mb文件！")
            return
        
        # 填充表格
        self.table.setRowCount(len(maya_files))
        for row, (file, path, size, shot_name) in enumerate(maya_files):
            # 选择列（复选框）
            chk_item = QtWidgets.QTableWidgetItem()
            chk_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            chk_item.setCheckState(QtCore.Qt.Checked)
            self.table.setItem(row, 0, chk_item)
            
            # 文件名列
            file_item = QtWidgets.QTableWidgetItem(file)
            file_item.setData(QtCore.Qt.UserRole, {
                "file_name": file, 
                "file_path": path, 
                "size": size, 
                "shot_name": shot_name
            })
            self.table.setItem(row, 1, file_item)
            
            # 路径列
            path_item = QtWidgets.QTableWidgetItem(path)
            path_item.setToolTip(path)
            self.table.setItem(row, 2, path_item)
            
            # 大小列
            size_item = QtWidgets.QTableWidgetItem(f"{size:.2f}")
            size_item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.table.setItem(row, 3, size_item)
            
            # 镜头号列
            shot_item = QtWidgets.QTableWidgetItem(shot_name)
            self.table.setItem(row, 4, shot_item)
            
            # 开始帧列
            start_frame_item = QtWidgets.QTableWidgetItem(str(self.start_frame_spin.value()))
            start_frame_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(row, 5, start_frame_item)
            
            # 结束帧列
            end_frame_item = QtWidgets.QTableWidgetItem(str(self.end_frame_spin.value()))
            end_frame_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(row, 6, end_frame_item)
            
            # 状态列
            status_item = QtWidgets.QTableWidgetItem(u"等待处理")
            status_item.setTextAlignment(QtCore.Qt.AlignCenter)
            self.table.setItem(row, 7, status_item)
        
        # 调整列宽
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 60)  # 选择列宽度
        self.table.setColumnWidth(3, 80)   # 大小列宽度
        self.table.setColumnWidth(4, 100)  # 镜头号列宽度
        self.table.setColumnWidth(5, 80)   # 开始帧列宽度
        self.table.setColumnWidth(6, 80)   # 结束帧列宽度
        self.table.setColumnWidth(7, 100)  # 状态列宽度
        
        cmds.inViewMessage(
            amg=u"找到 {} 个Maya文件".format(len(maya_files)),
            pos='midCenter', 
            fade=True
        )
    
    def on_cell_double_clicked(self, row, column):
        """双击表格单元格时启用编辑"""
        if column in [5, 6]:  # 开始帧和结束帧列
            item = self.table.item(row, column)
            if item:
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                self.table.editItem(item)
    
    def apply_global_frame_range(self):
        """将全局帧范围应用到所有文件"""
        global_start = self.start_frame_spin.value()
        global_end = self.end_frame_spin.value()
        
        for row in range(self.table.rowCount()):
            # 更新开始帧
            start_item = self.table.item(row, 5)
            if start_item:
                start_item.setText(str(global_start))
            
            # 更新结束帧
            end_item = self.table.item(row, 6)
            if end_item:
                end_item.setText(str(global_end))
        
        cmds.inViewMessage(
            amg=u"已应用全局帧范围到所有文件",
            pos='midCenter', 
            fade=True
        )
    
    def apply_selected_frame_range(self):
        """将文件帧范围应用到选中文件"""
        file_start = self.file_start_frame_spin.value()
        file_end = self.file_end_frame_spin.value()
        
        selected_rows = set(item.row() for item in self.table.selectedItems())
        
        if not selected_rows:
            cmds.warning(u"请先选择文件！")
            return
        
        for row in selected_rows:
            # 更新开始帧
            start_item = self.table.item(row, 5)
            if start_item:
                start_item.setText(str(file_start))
            
            # 更新结束帧
            end_item = self.table.item(row, 6)
            if end_item:
                end_item.setText(str(file_end))
        
        cmds.inViewMessage(
            amg=u"已应用帧范围到 {} 个文件".format(len(selected_rows)),
            pos='midCenter', 
            fade=True
        )
    
    def show_context_menu(self, position):
        """右键菜单"""
        menu = QtWidgets.QMenu()
        
        # 在资源管理器中显示
        open_action = menu.addAction(u"在资源管理器中显示")
        open_action.triggered.connect(self.show_in_explorer)
        
        # 复制文件路径
        copy_action = menu.addAction(u"复制文件路径")
        copy_action.triggered.connect(self.copy_file_path)
        
        # 显示错误信息
        item = self.table.itemAt(position)
        if item and item.row() >= 0:
            status_item = self.table.item(item.row(), 7)
            if status_item and status_item.text() == u"处理失败":
                error_action = menu.addAction(u"显示错误信息")
                error_action.triggered.connect(lambda: self.show_error_message(item.row()))
        
        menu.exec_(self.table.viewport().mapToGlobal(position))
    
    def show_in_explorer(self):
        """在资源管理器中打开"""
        selected = self.table.selectedItems()
        if not selected:
            return
        
        file_path = self.table.item(selected[0].row(), 2).text()
        if os.path.exists(file_path):
            os.startfile(os.path.dirname(file_path))
    
    def copy_file_path(self):
        """复制文件路径到剪贴板"""
        selected = self.table.selectedItems()
        if not selected:
            return
        
        file_path = self.table.item(selected[0].row(), 2).text()
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(file_path)
        
        cmds.inViewMessage(
            amg=u"文件路径已复制到剪贴板",
            pos='midCenter', 
            fade=True
        )
    
    def show_error_message(self, row):
        """显示错误信息"""
        status_item = self.table.item(row, 7)
        if status_item and status_item.data(QtCore.Qt.UserRole):
            QtWidgets.QMessageBox.critical(
                self, 
                u"处理错误", 
                status_item.data(QtCore.Qt.UserRole)
            )
    
    def process_selected_files(self):
        """处理选中的文件"""
        output_folder = self.folder2_lineedit.text().replace('\\', '/')
        if not output_folder:
            cmds.warning(u"请选择输出文件夹！")
            cmds.inViewMessage(
                amg=u"请选择输出文件夹！",
                pos='midCenter', 
                fade=True
            )
            return
        
        # 获取选中的文件
        publish_items = []
        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item and chk_item.checkState() == QtCore.Qt.Checked:
                file_item = self.table.item(row, 1)
                publish_items.append((row, file_item.data(QtCore.Qt.UserRole)))
        
        if not publish_items:
            cmds.warning(u"请确认勾选导出项")
            cmds.inViewMessage(
                amg=u"请确认勾选导出项",
                pos='midCenter', 
                fade=True
            )
            return
        
        # 处理文件
        success_count = 0
        for row, item_data in publish_items:
            try:
                # 更新状态
                status_item = self.table.item(row, 7)
                status_item.setText(u"处理中...")
                status_item.setBackground(QtGui.QColor(255, 255, 200))  # 浅黄色背景
                self.table.viewport().update()
                
                # 获取帧范围
                start_frame = int(self.table.item(row, 5).text())
                end_frame = int(self.table.item(row, 6).text())
                print(f"帧范围: {start_frame} - {end_frame}")  
                start = start_frame - 8  # 前后各加8帧缓冲
                end = end_frame + 8
                
                # 处理文件
                core_run(item_data['file_path'], item_data['shot_name'], start, end,output_folder)
                
                # 更新状态
                status_item.setText(u"处理成功")
                status_item.setBackground(QtGui.QColor(200, 255, 200))  # 浅绿色背景
                success_count += 1
            except Exception as e:
                # 记录错误
                error_msg = traceback.format_exc()
                status_item.setText(u"处理失败")
                status_item.setBackground(QtGui.QColor(255, 200, 200))  # 浅红色背景
                status_item.setData(QtCore.Qt.UserRole, error_msg)
                print(f"处理失败: {error_msg}")
        
        # 显示结果
        cmds.confirmDialog(
            title=u"处理完成",
            message=u"已处理 {} 个文件\n成功: {} | 失败: {}".format(
                len(publish_items), 
                success_count, 
                len(publish_items) - success_count
            ),
            button=[u"确定"],
            defaultButton=u"确定"
        )

# ===================== 显示UI =====================
def main():
    global folder_selector_ui
    try:
        folder_selector_ui.close()
    except:
        pass
    folder_selector_ui = FolderSelectorUI(parent=QtWidgets.QApplication.activeWindow())
    folder_selector_ui.show()
