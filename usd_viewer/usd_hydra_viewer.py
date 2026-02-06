"""
USD Intermediate Viewer - PySide6 + Hydra 기반 중급 뷰어
=======================================================

학습 목표:
- USD Hydra 렌더링 프레임워크 이해
- Storm (OpenGL) 렌더러 활용
- PySide6 GUI 통합
- 머티리얼, 조명, 카메라 고급 설정

의존성:
    pip install PySide6 numpy usd-core

사용법:
    python usd_hydra_viewer.py [usd_file_path]
"""

import sys
import math
import numpy as np
from pathlib import Path

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QToolBar, QStatusBar, QFileDialog, QSlider, QLabel, QComboBox,
        QCheckBox, QGroupBox, QDockWidget, QTreeWidget, QTreeWidgetItem,
        QPushButton, QSpinBox, QDoubleSpinBox, QSplitter, QFrame
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QSize
    from PySide6.QtGui import QAction, QIcon, QKeySequence
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
except ImportError:
    print("PySide6가 필요합니다:")
    print("  pip install PySide6")
    sys.exit(1)

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print("PyOpenGL이 필요합니다:")
    print("  pip install PyOpenGL PyOpenGL_accelerate")
    sys.exit(1)

# USD 관련 임포트
USD_HYDRA_AVAILABLE = False
try:
    from pxr import Usd, UsdGeom, UsdLux, UsdShade, Sdf, Gf, Tf
    from pxr import UsdImagingGL
    USD_HYDRA_AVAILABLE = True
    print("USD Hydra 렌더러 사용 가능")
except ImportError:
    print("경고: USD Hydra 렌더러를 사용할 수 없습니다.")
    print("  pip install usd-core")


class Camera:
    """고급 Orbit 카메라 (USD GfCamera 호환)"""
    
    def __init__(self):
        self.distance = 10.0
        self.azimuth = 45.0
        self.elevation = 30.0
        self.target = Gf.Vec3d(0, 0, 0) if USD_HYDRA_AVAILABLE else [0, 0, 0]
        
        self.fov = 45.0
        self.near = 0.1
        self.far = 10000.0
        
        # 마우스 상태
        self.last_pos = None
        self.rotating = False
        self.panning = False
    
    def get_position(self):
        """카메라 월드 위치 반환"""
        az = math.radians(self.azimuth)
        el = math.radians(self.elevation)
        
        x = self.distance * math.cos(el) * math.sin(az)
        y = self.distance * math.sin(el)
        z = self.distance * math.cos(el) * math.cos(az)
        
        if USD_HYDRA_AVAILABLE:
            target = self.target
            return Gf.Vec3d(target[0] + x, target[1] + y, target[2] + z)
        else:
            return [self.target[0] + x, self.target[1] + y, self.target[2] + z]
    
    def get_view_matrix(self):
        """뷰 행렬 반환"""
        eye = self.get_position()
        target = self.target
        up = Gf.Vec3d(0, 1, 0) if USD_HYDRA_AVAILABLE else [0, 1, 0]
        
        if USD_HYDRA_AVAILABLE:
            return Gf.Matrix4d().SetLookAt(eye, target, up)
        else:
            # Fallback: numpy 행렬 계산
            return self._compute_lookat_matrix(eye, target, up)
    
    def _compute_lookat_matrix(self, eye, target, up):
        """LookAt 행렬 계산 (fallback)"""
        eye = np.array(eye)
        target = np.array(target)
        up = np.array(up)
        
        f = target - eye
        f = f / np.linalg.norm(f)
        
        r = np.cross(f, up)
        r = r / np.linalg.norm(r)
        
        u = np.cross(r, f)
        
        view = np.eye(4)
        view[0, :3] = r
        view[1, :3] = u
        view[2, :3] = -f
        view[:3, 3] = [-np.dot(r, eye), -np.dot(u, eye), np.dot(f, eye)]
        
        return view
    
    def get_projection_matrix(self, aspect):
        """투영 행렬 반환"""
        if USD_HYDRA_AVAILABLE:
            frustum = Gf.Frustum()
            frustum.SetPerspective(self.fov, aspect, self.near, self.far)
            return frustum.ComputeProjectionMatrix()
        else:
            return self._compute_perspective_matrix(aspect)
    
    def _compute_perspective_matrix(self, aspect):
        """투영 행렬 계산 (fallback)"""
        fov_rad = math.radians(self.fov)
        f = 1.0 / math.tan(fov_rad / 2.0)
        
        proj = np.zeros((4, 4))
        proj[0, 0] = f / aspect
        proj[1, 1] = f
        proj[2, 2] = (self.far + self.near) / (self.near - self.far)
        proj[2, 3] = (2 * self.far * self.near) / (self.near - self.far)
        proj[3, 2] = -1.0
        
        return proj
    
    def rotate(self, dx, dy):
        self.azimuth -= dx * 0.3
        self.elevation += dy * 0.3
        self.elevation = max(-89, min(89, self.elevation))
    
    def pan(self, dx, dy, viewport_width, viewport_height):
        scale = self.distance * 0.001
        az = math.radians(self.azimuth)
        
        right_x = math.cos(az) * dx * scale
        right_z = -math.sin(az) * dx * scale
        up_y = dy * scale
        
        if USD_HYDRA_AVAILABLE:
            self.target = Gf.Vec3d(
                self.target[0] - right_x,
                self.target[1] + up_y,
                self.target[2] - right_z
            )
        else:
            self.target[0] -= right_x
            self.target[1] += up_y
            self.target[2] -= right_z
    
    def zoom(self, delta):
        self.distance *= (1.0 - delta * 0.1)
        self.distance = max(0.01, min(10000, self.distance))
    
    def frame_bounds(self, bbox_min, bbox_max):
        """바운딩 박스에 맞게 카메라 위치 조정"""
        center = [
            (bbox_min[0] + bbox_max[0]) / 2,
            (bbox_min[1] + bbox_max[1]) / 2,
            (bbox_min[2] + bbox_max[2]) / 2
        ]
        
        size = max(
            bbox_max[0] - bbox_min[0],
            bbox_max[1] - bbox_min[1],
            bbox_max[2] - bbox_min[2]
        )
        
        if USD_HYDRA_AVAILABLE:
            self.target = Gf.Vec3d(*center)
        else:
            self.target = center
        
        self.distance = size * 2.0 if size > 0 else 10.0


class HydraViewport(QOpenGLWidget):
    """USD Hydra 렌더링 뷰포트"""
    
    sceneLoaded = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.camera = Camera()
        self.stage = None
        self.renderer = None
        
        # 렌더링 옵션
        self.draw_mode = 'shaded'  # shaded, wireframe, points
        self.show_grid = True
        self.show_axes = True
        self.enable_lighting = True
        self.background_color = (0.18, 0.18, 0.22, 1.0)
        
        # 선택 상태
        self.selected_prim = None
        
        # 마우스 추적
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 애니메이션
        self.time_code = 0.0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.advance_time)
    
    def initializeGL(self):
        """OpenGL 초기화"""
        glClearColor(*self.background_color)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_MULTISAMPLE)
        
        # 조명 초기화
        if self.enable_lighting:
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glLightfv(GL_LIGHT0, GL_POSITION, [1, 1, 1, 0])
            glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1])
            glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1])
        
        # Hydra 렌더러 초기화
        if USD_HYDRA_AVAILABLE:
            self.init_hydra_renderer()
    
    def init_hydra_renderer(self):
        """Hydra 렌더러 초기화"""
        try:
            self.renderer = UsdImagingGL.Engine()
            print("Hydra 렌더러 초기화 완료")
        except Exception as e:
            print(f"Hydra 렌더러 초기화 실패: {e}")
            self.renderer = None
    
    def resizeGL(self, w, h):
        """뷰포트 리사이즈"""
        glViewport(0, 0, w, h)
        
        if self.renderer and USD_HYDRA_AVAILABLE:
            self.renderer.SetRenderViewport((0, 0, w, h))
    
    def paintGL(self):
        """렌더링"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        w, h = self.width(), self.height()
        aspect = w / h if h > 0 else 1.0
        
        # 투영 행렬 설정
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.camera.fov, aspect, self.camera.near, self.camera.far)
        
        # 뷰 행렬 설정
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        eye = self.camera.get_position()
        target = self.camera.target
        
        if USD_HYDRA_AVAILABLE:
            gluLookAt(eye[0], eye[1], eye[2],
                     target[0], target[1], target[2],
                     0, 1, 0)
        else:
            gluLookAt(*eye, *target, 0, 1, 0)
        
        # 보조 요소 렌더링
        if self.show_grid:
            self.draw_grid()
        if self.show_axes:
            self.draw_axes()
        
        # USD 씬 렌더링
        if self.stage and self.renderer and USD_HYDRA_AVAILABLE:
            self.render_hydra()
        elif self.stage:
            self.render_fallback()
    
    def render_hydra(self):
        """Hydra를 통한 USD 렌더링"""
        try:
            w, h = self.width(), self.height()
            aspect = w / h if h > 0 else 1.0
            
            # Hydra 렌더 파라미터 설정
            params = UsdImagingGL.RenderParams()
            params.frame = Usd.TimeCode(self.time_code)
            params.clearColor = Gf.Vec4f(*self.background_color)
            
            # 드로우 모드 설정
            if self.draw_mode == 'wireframe':
                params.drawMode = UsdImagingGL.DrawMode.DRAW_WIREFRAME
            elif self.draw_mode == 'points':
                params.drawMode = UsdImagingGL.DrawMode.DRAW_POINTS
            else:
                params.drawMode = UsdImagingGL.DrawMode.DRAW_SHADED_SMOOTH
            
            params.enableLighting = self.enable_lighting
            params.enableSceneMaterials = True
            
            # 카메라 설정
            view_matrix = self.camera.get_view_matrix()
            proj_matrix = self.camera.get_projection_matrix(aspect)
            
            # 렌더링 실행
            root = self.stage.GetPseudoRoot()
            self.renderer.SetRenderViewport((0, 0, w, h))
            self.renderer.SetCameraState(view_matrix, proj_matrix)
            self.renderer.Render(root, params)
            
        except Exception as e:
            print(f"Hydra 렌더링 오류: {e}")
            self.render_fallback()
    
    def render_fallback(self):
        """Hydra 없이 기본 렌더링"""
        if not self.stage:
            return
        
        glEnable(GL_LIGHTING)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        for prim in self.stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                self.render_mesh_simple(prim)
    
    def render_mesh_simple(self, prim):
        """간단한 메시 렌더링"""
        mesh = UsdGeom.Mesh(prim)
        
        points = mesh.GetPointsAttr().Get(self.time_code)
        indices = mesh.GetFaceVertexIndicesAttr().Get()
        counts = mesh.GetFaceVertexCountsAttr().Get()
        
        if not points or not indices or not counts:
            return
        
        # 변환 행렬 적용
        xform = UsdGeom.Xformable(prim)
        world_xform = xform.ComputeLocalToWorldTransform(self.time_code)
        
        glPushMatrix()
        glMultMatrixd(list(world_xform.GetArray()))
        
        # 색상
        colors = mesh.GetDisplayColorAttr().Get()
        if colors and len(colors) > 0:
            glColor3f(colors[0][0], colors[0][1], colors[0][2])
        else:
            glColor3f(0.7, 0.7, 0.8)
        
        # 삼각형 렌더링
        glBegin(GL_TRIANGLES)
        idx = 0
        for count in counts:
            if count >= 3:
                v0 = points[indices[idx]]
                for i in range(1, count - 1):
                    v1 = points[indices[idx + i]]
                    v2 = points[indices[idx + i + 1]]
                    
                    # 노멀 계산
                    e1 = [v1[j] - v0[j] for j in range(3)]
                    e2 = [v2[j] - v0[j] for j in range(3)]
                    n = [
                        e1[1]*e2[2] - e1[2]*e2[1],
                        e1[2]*e2[0] - e1[0]*e2[2],
                        e1[0]*e2[1] - e1[1]*e2[0]
                    ]
                    length = math.sqrt(sum(x*x for x in n))
                    if length > 0:
                        n = [x/length for x in n]
                    
                    glNormal3f(*n)
                    glVertex3f(*v0)
                    glVertex3f(*v1)
                    glVertex3f(*v2)
            idx += count
        glEnd()
        
        glPopMatrix()
    
    def draw_grid(self, size=10, divisions=20):
        """그리드 렌더링"""
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.35)
        
        step = size / divisions
        half = size / 2
        
        glBegin(GL_LINES)
        for i in range(divisions + 1):
            pos = -half + i * step
            glVertex3f(-half, 0, pos)
            glVertex3f(half, 0, pos)
            glVertex3f(pos, 0, -half)
            glVertex3f(pos, 0, half)
        glEnd()
        
        if self.enable_lighting:
            glEnable(GL_LIGHTING)
    
    def draw_axes(self, length=1.0):
        """좌표축 렌더링"""
        glDisable(GL_LIGHTING)
        glLineWidth(2.0)
        
        glBegin(GL_LINES)
        glColor3f(1, 0.2, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)
        
        glColor3f(0.2, 1, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)
        
        glColor3f(0.2, 0.2, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)
        glEnd()
        
        glLineWidth(1.0)
        if self.enable_lighting:
            glEnable(GL_LIGHTING)
    
    def load_stage(self, filepath):
        """USD 스테이지 로드"""
        if not USD_HYDRA_AVAILABLE:
            print("USD 라이브러리가 필요합니다.")
            return False
        
        try:
            self.stage = Usd.Stage.Open(filepath)
            if not self.stage:
                print(f"스테이지를 열 수 없습니다: {filepath}")
                return False
            
            print(f"USD 로드 성공: {filepath}")
            
            # 바운딩 박스 계산
            bbox_cache = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                [UsdGeom.Tokens.default_]
            )
            
            root = self.stage.GetPseudoRoot()
            bbox = bbox_cache.ComputeWorldBound(root)
            bbox_range = bbox.ComputeAlignedRange()
            
            if not bbox_range.IsEmpty():
                min_pt = bbox_range.GetMin()
                max_pt = bbox_range.GetMax()
                self.camera.frame_bounds(
                    [min_pt[0], min_pt[1], min_pt[2]],
                    [max_pt[0], max_pt[1], max_pt[2]]
                )
            
            # Hydra에 스테이지 설정
            if self.renderer:
                self.renderer.SetRenderViewport((0, 0, self.width(), self.height()))
            
            self.sceneLoaded.emit(filepath)
            self.update()
            return True
            
        except Exception as e:
            print(f"USD 로드 오류: {e}")
            return False
    
    def create_sample_stage(self):
        """샘플 스테이지 생성"""
        if not USD_HYDRA_AVAILABLE:
            return
        
        self.stage = Usd.Stage.CreateInMemory()
        
        # 큐브 생성
        cube = UsdGeom.Cube.Define(self.stage, '/World/Cube')
        cube.GetSizeAttr().Set(1.0)
        cube.AddTranslateOp().Set(Gf.Vec3d(-1.5, 0.5, 0))
        cube.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.5, 0.9)])
        
        # 구 생성
        sphere = UsdGeom.Sphere.Define(self.stage, '/World/Sphere')
        sphere.GetRadiusAttr().Set(0.8)
        sphere.AddTranslateOp().Set(Gf.Vec3d(1.5, 0.8, 0))
        sphere.GetDisplayColorAttr().Set([Gf.Vec3f(0.9, 0.3, 0.2)])
        
        # 실린더 생성
        cylinder = UsdGeom.Cylinder.Define(self.stage, '/World/Cylinder')
        cylinder.GetRadiusAttr().Set(0.5)
        cylinder.GetHeightAttr().Set(2.0)
        cylinder.AddTranslateOp().Set(Gf.Vec3d(0, 1, -2))
        cylinder.GetDisplayColorAttr().Set([Gf.Vec3f(0.3, 0.8, 0.3)])
        
        # 바닥 평면
        plane = UsdGeom.Mesh.Define(self.stage, '/World/Ground')
        plane.GetPointsAttr().Set([
            Gf.Vec3f(-5, 0, -5), Gf.Vec3f(5, 0, -5),
            Gf.Vec3f(5, 0, 5), Gf.Vec3f(-5, 0, 5)
        ])
        plane.GetFaceVertexIndicesAttr().Set([0, 1, 2, 3])
        plane.GetFaceVertexCountsAttr().Set([4])
        plane.GetDisplayColorAttr().Set([Gf.Vec3f(0.4, 0.4, 0.45)])
        
        # 조명
        light = UsdLux.DistantLight.Define(self.stage, '/World/Light')
        light.GetIntensityAttr().Set(1.0)
        light.AddRotateXYZOp().Set(Gf.Vec3f(-45, 30, 0))
        
        self.camera.frame_bounds([-5, 0, -5], [5, 3, 5])
        
        if self.renderer:
            self.renderer.SetRenderViewport((0, 0, self.width(), self.height()))
        
        self.sceneLoaded.emit("Sample Scene")
        self.update()
    
    def advance_time(self):
        """애니메이션 시간 진행"""
        self.time_code += 1.0
        self.update()
    
    # === 마우스 이벤트 ===
    
    def mousePressEvent(self, event):
        self.camera.last_pos = event.position()
        
        if event.button() == Qt.LeftButton:
            self.camera.rotating = True
        elif event.button() == Qt.RightButton:
            self.camera.panning = True
    
    def mouseReleaseEvent(self, event):
        self.camera.rotating = False
        self.camera.panning = False
    
    def mouseMoveEvent(self, event):
        if not self.camera.last_pos:
            return
        
        pos = event.position()
        dx = pos.x() - self.camera.last_pos.x()
        dy = pos.y() - self.camera.last_pos.y()
        self.camera.last_pos = pos
        
        if self.camera.rotating:
            self.camera.rotate(dx, dy)
            self.update()
        elif self.camera.panning:
            self.camera.pan(dx, dy, self.width(), self.height())
            self.update()
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.camera.zoom(delta)
        self.update()
    
    def keyPressEvent(self, event):
        key = event.key()
        
        if key == Qt.Key_F:
            # 씬에 맞게 프레임
            if self.stage and USD_HYDRA_AVAILABLE:
                bbox_cache = UsdGeom.BBoxCache(
                    Usd.TimeCode.Default(),
                    [UsdGeom.Tokens.default_]
                )
                bbox = bbox_cache.ComputeWorldBound(self.stage.GetPseudoRoot())
                bbox_range = bbox.ComputeAlignedRange()
                if not bbox_range.IsEmpty():
                    min_pt = bbox_range.GetMin()
                    max_pt = bbox_range.GetMax()
                    self.camera.frame_bounds(
                        [min_pt[0], min_pt[1], min_pt[2]],
                        [max_pt[0], max_pt[1], max_pt[2]]
                    )
            self.update()
        
        elif key == Qt.Key_G:
            self.show_grid = not self.show_grid
            self.update()
        
        elif key == Qt.Key_A:
            self.show_axes = not self.show_axes
            self.update()
        
        elif key == Qt.Key_W:
            modes = ['shaded', 'wireframe', 'points']
            idx = (modes.index(self.draw_mode) + 1) % len(modes)
            self.draw_mode = modes[idx]
            self.update()
        
        elif key == Qt.Key_L:
            self.enable_lighting = not self.enable_lighting
            self.update()


class SceneHierarchyWidget(QDockWidget):
    """씬 계층 구조 패널"""
    
    primSelected = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__("Scene Hierarchy", parent)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Prim", "Type"])
        self.tree.itemClicked.connect(self.on_item_clicked)
        
        self.setWidget(self.tree)
    
    def update_hierarchy(self, stage):
        """계층 구조 업데이트"""
        self.tree.clear()
        
        if not stage:
            return
        
        def add_children(parent_item, prim):
            for child in prim.GetChildren():
                item = QTreeWidgetItem([
                    child.GetName(),
                    child.GetTypeName()
                ])
                parent_item.addChild(item)
                item.setData(0, Qt.UserRole, str(child.GetPath()))
                add_children(item, child)
        
        root = stage.GetPseudoRoot()
        for child in root.GetChildren():
            item = QTreeWidgetItem([
                child.GetName(),
                child.GetTypeName()
            ])
            self.tree.addTopLevelItem(item)
            item.setData(0, Qt.UserRole, str(child.GetPath()))
            add_children(item, child)
        
        self.tree.expandAll()
    
    def on_item_clicked(self, item, column):
        path = item.data(0, Qt.UserRole)
        if path:
            self.primSelected.emit(path)


class PropertiesWidget(QDockWidget):
    """속성 패널"""
    
    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.info_label = QLabel("선택된 프림 없음")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        self.setWidget(widget)
    
    def show_prim_properties(self, stage, prim_path):
        """프림 속성 표시"""
        if not stage:
            return
        
        prim = stage.GetPrimAtPath(prim_path)
        if not prim:
            return
        
        info = f"Path: {prim_path}\n"
        info += f"Type: {prim.GetTypeName()}\n"
        info += f"Valid: {prim.IsValid()}\n"
        info += f"Active: {prim.IsActive()}\n"
        
        if prim.IsA(UsdGeom.Mesh):
            mesh = UsdGeom.Mesh(prim)
            points = mesh.GetPointsAttr().Get()
            faces = mesh.GetFaceVertexCountsAttr().Get()
            if points:
                info += f"Vertices: {len(points)}\n"
            if faces:
                info += f"Faces: {len(faces)}\n"
        
        self.info_label.setText(info)


class USDHydraViewer(QMainWindow):
    """USD Hydra 뷰어 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("USD Hydra Viewer")
        self.setMinimumSize(1280, 720)
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        
        # 샘플 씬 생성
        self.viewport.create_sample_stage()
        self.hierarchy.update_hierarchy(self.viewport.stage)
    
    def setup_ui(self):
        """UI 구성"""
        # 메인 뷰포트
        self.viewport = HydraViewport()
        self.setCentralWidget(self.viewport)
        
        # 계층 구조 패널
        self.hierarchy = SceneHierarchyWidget(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.hierarchy)
        
        # 속성 패널
        self.properties = PropertiesWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties)
        
        # 연결
        self.hierarchy.primSelected.connect(self.on_prim_selected)
        self.viewport.sceneLoaded.connect(self.on_scene_loaded)
        
        # 상태바
        self.statusBar().showMessage("준비")
    
    def setup_menu(self):
        """메뉴 구성"""
        menubar = self.menuBar()
        
        # File 메뉴
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open USD...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View 메뉴
        view_menu = menubar.addMenu("View")
        
        frame_action = QAction("Frame All (F)", self)
        frame_action.triggered.connect(lambda: self.viewport.keyPressEvent(
            type('', (), {'key': lambda: Qt.Key_F})()
        ))
        view_menu.addAction(frame_action)
        
        view_menu.addSeparator()
        
        grid_action = QAction("Toggle Grid (G)", self)
        grid_action.triggered.connect(lambda: setattr(
            self.viewport, 'show_grid', not self.viewport.show_grid
        ) or self.viewport.update())
        view_menu.addAction(grid_action)
        
        axes_action = QAction("Toggle Axes (A)", self)
        axes_action.triggered.connect(lambda: setattr(
            self.viewport, 'show_axes', not self.viewport.show_axes
        ) or self.viewport.update())
        view_menu.addAction(axes_action)
    
    def setup_toolbar(self):
        """툴바 구성"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 드로우 모드 콤보박스
        mode_label = QLabel(" Draw Mode: ")
        toolbar.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Shaded", "Wireframe", "Points"])
        self.mode_combo.currentTextChanged.connect(self.on_draw_mode_changed)
        toolbar.addWidget(self.mode_combo)
        
        toolbar.addSeparator()
        
        # 조명 토글
        self.lighting_check = QCheckBox("Lighting")
        self.lighting_check.setChecked(True)
        self.lighting_check.stateChanged.connect(self.on_lighting_changed)
        toolbar.addWidget(self.lighting_check)
        
        toolbar.addSeparator()
        
        # 그리드/축 토글
        self.grid_check = QCheckBox("Grid")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(
            lambda s: setattr(self.viewport, 'show_grid', s == Qt.Checked) or self.viewport.update()
        )
        toolbar.addWidget(self.grid_check)
        
        self.axes_check = QCheckBox("Axes")
        self.axes_check.setChecked(True)
        self.axes_check.stateChanged.connect(
            lambda s: setattr(self.viewport, 'show_axes', s == Qt.Checked) or self.viewport.update()
        )
        toolbar.addWidget(self.axes_check)
    
    def open_file(self):
        """파일 열기 다이얼로그"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open USD File", "",
            "USD Files (*.usd *.usda *.usdc *.usdz);;All Files (*)"
        )
        
        if filepath:
            if self.viewport.load_stage(filepath):
                self.hierarchy.update_hierarchy(self.viewport.stage)
    
    def on_scene_loaded(self, name):
        """씬 로드 완료"""
        self.statusBar().showMessage(f"로드됨: {name}")
        self.setWindowTitle(f"USD Hydra Viewer - {Path(name).name if Path(name).exists() else name}")
    
    def on_prim_selected(self, prim_path):
        """프림 선택됨"""
        self.statusBar().showMessage(f"선택: {prim_path}")
        self.properties.show_prim_properties(self.viewport.stage, prim_path)
    
    def on_draw_mode_changed(self, text):
        """드로우 모드 변경"""
        mode_map = {
            "Shaded": "shaded",
            "Wireframe": "wireframe",
            "Points": "points"
        }
        self.viewport.draw_mode = mode_map.get(text, "shaded")
        self.viewport.update()
    
    def on_lighting_changed(self, state):
        """조명 토글"""
        self.viewport.enable_lighting = (state == Qt.Checked)
        self.viewport.update()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    viewer = USDHydraViewer()
    
    # 커맨드라인에서 파일 지정 시 로드
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if Path(filepath).exists():
            viewer.viewport.load_stage(filepath)
            viewer.hierarchy.update_hierarchy(viewer.viewport.stage)
    
    viewer.show()
    
    print("""
=== USD Hydra Viewer ===
조작법:
  마우스 좌클릭 드래그: 회전
  마우스 우클릭 드래그: 패닝
  마우스 휠: 줌
  
단축키:
  F: 씬에 맞게 프레임
  G: 그리드 토글
  A: 좌표축 토글
  W: 드로우 모드 순환
  L: 조명 토글
========================
""")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
