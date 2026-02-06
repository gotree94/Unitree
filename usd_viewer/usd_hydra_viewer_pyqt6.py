"""
USD Intermediate Viewer - PyQt6 + Hydra 기반 중급 뷰어
======================================================

PySide6 DLL 충돌 문제 발생 시 PyQt6 대체 버전

의존성:
    pip install PyQt6 PyOpenGL numpy usd-core

사용법:
    python usd_hydra_viewer_pyqt6.py [usd_file_path]
"""

import sys
import math
import numpy as np
from pathlib import Path

# PyQt6 임포트
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QToolBar, QStatusBar, QFileDialog, QSlider, QLabel, QComboBox,
        QCheckBox, QGroupBox, QDockWidget, QTreeWidget, QTreeWidgetItem,
        QPushButton, QSpinBox, QDoubleSpinBox, QSplitter, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
    from PyQt6.QtGui import QAction, QIcon, QKeySequence
    from PyQt6.QtOpenGLWidgets import QOpenGLWidget
except ImportError as e:
    print(f"PyQt6 import 오류: {e}")
    print("PyQt6가 필요합니다:")
    print("  pip install PyQt6")
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
    try:
        from pxr import UsdImagingGL
        USD_HYDRA_AVAILABLE = True
        print("USD Hydra 렌더러 사용 가능")
    except ImportError:
        print("경고: UsdImagingGL을 사용할 수 없습니다. Fallback 렌더러 사용")
except ImportError:
    print("경고: USD 라이브러리를 사용할 수 없습니다.")
    print("  pip install usd-core")


class Camera:
    """고급 Orbit 카메라"""
    
    def __init__(self):
        self.distance = 10.0
        self.azimuth = 45.0
        self.elevation = 30.0
        self.target = [0.0, 0.0, 0.0]
        
        self.fov = 45.0
        self.near = 0.1
        self.far = 10000.0
        
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
        
        return [self.target[0] + x, self.target[1] + y, self.target[2] + z]
    
    def rotate(self, dx, dy):
        self.azimuth -= dx * 0.3
        self.elevation += dy * 0.3
        self.elevation = max(-89, min(89, self.elevation))
    
    def pan(self, dx, dy):
        scale = self.distance * 0.001
        az = math.radians(self.azimuth)
        
        right_x = math.cos(az) * dx * scale
        right_z = -math.sin(az) * dx * scale
        up_y = dy * scale
        
        self.target[0] -= right_x
        self.target[1] += up_y
        self.target[2] -= right_z
    
    def zoom(self, delta):
        self.distance *= (1.0 - delta * 0.1)
        self.distance = max(0.01, min(10000, self.distance))
    
    def frame_bounds(self, bbox_min, bbox_max):
        """바운딩 박스에 맞게 카메라 위치 조정"""
        self.target = [
            (bbox_min[0] + bbox_max[0]) / 2,
            (bbox_min[1] + bbox_max[1]) / 2,
            (bbox_min[2] + bbox_max[2]) / 2
        ]
        
        size = max(
            bbox_max[0] - bbox_min[0],
            bbox_max[1] - bbox_min[1],
            bbox_max[2] - bbox_min[2]
        )
        
        self.distance = size * 2.0 if size > 0 else 10.0


class GLViewport(QOpenGLWidget):
    """OpenGL 렌더링 뷰포트"""
    
    sceneLoaded = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.camera = Camera()
        self.stage = None
        self.renderer = None
        self.time_code = 0.0
        
        # 렌더링 옵션
        self.draw_mode = 'shaded'
        self.show_grid = True
        self.show_axes = True
        self.enable_lighting = True
        self.background_color = (0.18, 0.18, 0.22, 1.0)
        
        # 메시 캐시
        self.mesh_cache = []
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def initializeGL(self):
        """OpenGL 초기화"""
        glClearColor(*self.background_color)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_MULTISAMPLE)
        
        # 조명 설정
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [1, 1, 1, 0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1, 1, 1, 1])
        
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Hydra 렌더러 초기화 시도
        if USD_HYDRA_AVAILABLE:
            try:
                self.renderer = UsdImagingGL.Engine()
                print("Hydra 렌더러 초기화 완료")
            except Exception as e:
                print(f"Hydra 초기화 실패: {e}")
                self.renderer = None
    
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        if self.renderer:
            self.renderer.SetRenderViewport((0, 0, w, h))
    
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        w, h = self.width(), self.height()
        aspect = w / h if h > 0 else 1.0
        
        # 투영 행렬
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.camera.fov, aspect, self.camera.near, self.camera.far)
        
        # 뷰 행렬
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        eye = self.camera.get_position()
        target = self.camera.target
        gluLookAt(eye[0], eye[1], eye[2],
                  target[0], target[1], target[2],
                  0, 1, 0)
        
        # 조명 위치 업데이트
        glLightfv(GL_LIGHT0, GL_POSITION, [eye[0], eye[1] + 10, eye[2], 1])
        
        # 보조 요소
        if self.show_grid:
            self.draw_grid()
        if self.show_axes:
            self.draw_axes()
        
        # USD 씬 렌더링
        if self.stage:
            if self.renderer and USD_HYDRA_AVAILABLE:
                self.render_hydra()
            else:
                self.render_fallback()
    
    def render_hydra(self):
        """Hydra를 통한 USD 렌더링"""
        try:
            w, h = self.width(), self.height()
            aspect = w / h if h > 0 else 1.0
            
            params = UsdImagingGL.RenderParams()
            params.frame = Usd.TimeCode(self.time_code)
            params.clearColor = Gf.Vec4f(*self.background_color)
            
            if self.draw_mode == 'wireframe':
                params.drawMode = UsdImagingGL.DrawMode.DRAW_WIREFRAME
            elif self.draw_mode == 'points':
                params.drawMode = UsdImagingGL.DrawMode.DRAW_POINTS
            else:
                params.drawMode = UsdImagingGL.DrawMode.DRAW_SHADED_SMOOTH
            
            params.enableLighting = self.enable_lighting
            params.enableSceneMaterials = True
            
            # 뷰/투영 행렬 계산
            eye = self.camera.get_position()
            target = self.camera.target
            
            view_matrix = Gf.Matrix4d().SetLookAt(
                Gf.Vec3d(*eye),
                Gf.Vec3d(*target),
                Gf.Vec3d(0, 1, 0)
            )
            
            frustum = Gf.Frustum()
            frustum.SetPerspective(self.camera.fov, aspect, self.camera.near, self.camera.far)
            proj_matrix = frustum.ComputeProjectionMatrix()
            
            self.renderer.SetRenderViewport((0, 0, w, h))
            self.renderer.SetCameraState(view_matrix, proj_matrix)
            self.renderer.Render(self.stage.GetPseudoRoot(), params)
            
        except Exception as e:
            print(f"Hydra 렌더링 오류: {e}")
            self.render_fallback()
    
    def render_fallback(self):
        """OpenGL 직접 렌더링 (Hydra 없이)"""
        if not self.stage:
            return
        
        if self.enable_lighting:
            glEnable(GL_LIGHTING)
        else:
            glDisable(GL_LIGHTING)
        
        for prim in self.stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                self.render_mesh(prim)
            elif prim.IsA(UsdGeom.Cube):
                self.render_cube(prim)
            elif prim.IsA(UsdGeom.Sphere):
                self.render_sphere(prim)
            elif prim.IsA(UsdGeom.Cylinder):
                self.render_cylinder(prim)
            elif prim.IsA(UsdGeom.Cone):
                self.render_cone(prim)
            elif prim.IsA(UsdGeom.Capsule):
                self.render_capsule(prim)
    
    def apply_transform(self, prim):
        """프림의 변환 행렬 적용"""
        xform = UsdGeom.Xformable(prim)
        world_xform = xform.ComputeLocalToWorldTransform(Usd.TimeCode(self.time_code))
        glMultMatrixd(list(world_xform.GetArray()))
    
    def get_display_color(self, prim, default=(0.7, 0.7, 0.8)):
        """프림의 표시 색상 가져오기"""
        gprim = UsdGeom.Gprim(prim)
        colors = gprim.GetDisplayColorAttr().Get()
        if colors and len(colors) > 0:
            return (colors[0][0], colors[0][1], colors[0][2])
        return default
    
    def render_mesh(self, prim):
        """메시 프림 렌더링"""
        mesh = UsdGeom.Mesh(prim)
        
        points = mesh.GetPointsAttr().Get(self.time_code)
        indices = mesh.GetFaceVertexIndicesAttr().Get()
        counts = mesh.GetFaceVertexCountsAttr().Get()
        
        if not points or not indices or not counts:
            return
        
        glPushMatrix()
        self.apply_transform(prim)
        
        color = self.get_display_color(prim)
        glColor3f(*color)
        
        if self.draw_mode == 'wireframe':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif self.draw_mode == 'points':
            glPolygonMode(GL_FRONT_AND_BACK, GL_POINT)
            glPointSize(3)
        
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
                    else:
                        n = [0, 1, 0]
                    
                    glNormal3f(*n)
                    glVertex3f(v0[0], v0[1], v0[2])
                    glVertex3f(v1[0], v1[1], v1[2])
                    glVertex3f(v2[0], v2[1], v2[2])
            idx += count
        glEnd()
        
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glPopMatrix()
    
    def render_cube(self, prim):
        """큐브 프림 렌더링"""
        cube = UsdGeom.Cube(prim)
        size = cube.GetSizeAttr().Get() or 1.0
        
        glPushMatrix()
        self.apply_transform(prim)
        
        color = self.get_display_color(prim, (0.3, 0.5, 0.8))
        glColor3f(*color)
        
        half = size / 2
        
        vertices = [
            (-half, -half, -half), (half, -half, -half),
            (half, half, -half), (-half, half, -half),
            (-half, -half, half), (half, -half, half),
            (half, half, half), (-half, half, half)
        ]
        
        faces = [
            (0, 1, 2, 3, (0, 0, -1)),  # 뒤
            (4, 7, 6, 5, (0, 0, 1)),   # 앞
            (0, 3, 7, 4, (-1, 0, 0)),  # 왼쪽
            (1, 5, 6, 2, (1, 0, 0)),   # 오른쪽
            (0, 4, 5, 1, (0, -1, 0)),  # 아래
            (3, 2, 6, 7, (0, 1, 0)),   # 위
        ]
        
        glBegin(GL_QUADS)
        for f in faces:
            glNormal3f(*f[4])
            for i in range(4):
                glVertex3f(*vertices[f[i]])
        glEnd()
        
        glPopMatrix()
    
    def render_sphere(self, prim):
        """구 프림 렌더링"""
        sphere = UsdGeom.Sphere(prim)
        radius = sphere.GetRadiusAttr().Get() or 1.0
        
        glPushMatrix()
        self.apply_transform(prim)
        
        color = self.get_display_color(prim, (0.8, 0.3, 0.3))
        glColor3f(*color)
        
        slices, stacks = 24, 16
        
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + float(i) / stacks)
            z0 = radius * math.sin(lat0)
            zr0 = radius * math.cos(lat0)
            
            lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
            z1 = radius * math.sin(lat1)
            zr1 = radius * math.cos(lat1)
            
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                lng = 2 * math.pi * float(j) / slices
                x = math.cos(lng)
                y = math.sin(lng)
                
                glNormal3f(x * zr0 / radius, y * zr0 / radius, z0 / radius)
                glVertex3f(x * zr0, y * zr0, z0)
                
                glNormal3f(x * zr1 / radius, y * zr1 / radius, z1 / radius)
                glVertex3f(x * zr1, y * zr1, z1)
            glEnd()
        
        glPopMatrix()
    
    def render_cylinder(self, prim):
        """실린더 프림 렌더링"""
        cylinder = UsdGeom.Cylinder(prim)
        radius = cylinder.GetRadiusAttr().Get() or 1.0
        height = cylinder.GetHeightAttr().Get() or 2.0
        
        glPushMatrix()
        self.apply_transform(prim)
        
        color = self.get_display_color(prim, (0.3, 0.7, 0.3))
        glColor3f(*color)
        
        slices = 24
        half_h = height / 2
        
        # 옆면
        glBegin(GL_QUAD_STRIP)
        for i in range(slices + 1):
            angle = 2 * math.pi * i / slices
            x = math.cos(angle)
            z = math.sin(angle)
            
            glNormal3f(x, 0, z)
            glVertex3f(x * radius, -half_h, z * radius)
            glVertex3f(x * radius, half_h, z * radius)
        glEnd()
        
        # 윗면
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(0, 1, 0)
        glVertex3f(0, half_h, 0)
        for i in range(slices + 1):
            angle = 2 * math.pi * i / slices
            glVertex3f(radius * math.cos(angle), half_h, radius * math.sin(angle))
        glEnd()
        
        # 아랫면
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(0, -1, 0)
        glVertex3f(0, -half_h, 0)
        for i in range(slices, -1, -1):
            angle = 2 * math.pi * i / slices
            glVertex3f(radius * math.cos(angle), -half_h, radius * math.sin(angle))
        glEnd()
        
        glPopMatrix()
    
    def render_cone(self, prim):
        """콘 프림 렌더링"""
        cone = UsdGeom.Cone(prim)
        radius = cone.GetRadiusAttr().Get() or 1.0
        height = cone.GetHeightAttr().Get() or 2.0
        
        glPushMatrix()
        self.apply_transform(prim)
        
        color = self.get_display_color(prim, (0.9, 0.7, 0.2))
        glColor3f(*color)
        
        slices = 24
        half_h = height / 2
        
        # 옆면
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(0, half_h, 0)
        for i in range(slices + 1):
            angle = 2 * math.pi * i / slices
            x = math.cos(angle)
            z = math.sin(angle)
            glNormal3f(x, radius / height, z)
            glVertex3f(x * radius, -half_h, z * radius)
        glEnd()
        
        # 바닥면
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(0, -1, 0)
        glVertex3f(0, -half_h, 0)
        for i in range(slices, -1, -1):
            angle = 2 * math.pi * i / slices
            glVertex3f(radius * math.cos(angle), -half_h, radius * math.sin(angle))
        glEnd()
        
        glPopMatrix()
    
    def render_capsule(self, prim):
        """캡슐 프림 렌더링 (간소화: 실린더로 대체)"""
        capsule = UsdGeom.Capsule(prim)
        radius = capsule.GetRadiusAttr().Get() or 0.5
        height = capsule.GetHeightAttr().Get() or 2.0
        
        glPushMatrix()
        self.apply_transform(prim)
        
        color = self.get_display_color(prim, (0.8, 0.5, 0.2))
        glColor3f(*color)
        
        slices = 24
        half_h = height / 2
        
        # 실린더 부분
        glBegin(GL_QUAD_STRIP)
        for i in range(slices + 1):
            angle = 2 * math.pi * i / slices
            x = math.cos(angle)
            z = math.sin(angle)
            glNormal3f(x, 0, z)
            glVertex3f(x * radius, -half_h, z * radius)
            glVertex3f(x * radius, half_h, z * radius)
        glEnd()
        
        # 반구 (위/아래) - 간소화
        for sign in [1, -1]:
            for lat_i in range(8):
                lat0 = (math.pi / 2) * lat_i / 8
                lat1 = (math.pi / 2) * (lat_i + 1) / 8
                
                y0 = sign * (half_h + radius * math.sin(lat0))
                r0 = radius * math.cos(lat0)
                y1 = sign * (half_h + radius * math.sin(lat1))
                r1 = radius * math.cos(lat1)
                
                glBegin(GL_QUAD_STRIP)
                for j in range(slices + 1):
                    angle = 2 * math.pi * j / slices
                    x = math.cos(angle)
                    z = math.sin(angle)
                    
                    glNormal3f(x * r0 / radius, sign * math.sin(lat0), z * r0 / radius)
                    glVertex3f(x * r0, y0, z * r0)
                    
                    glNormal3f(x * r1 / radius, sign * math.sin(lat1), z * r1 / radius)
                    glVertex3f(x * r1, y1, z * r1)
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
        try:
            from pxr import Usd, UsdGeom
        except ImportError:
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
            
            if self.renderer:
                self.renderer.SetRenderViewport((0, 0, self.width(), self.height()))
            
            self.sceneLoaded.emit(filepath)
            self.update()
            return True
            
        except Exception as e:
            print(f"USD 로드 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_sample_stage(self):
        """샘플 스테이지 생성"""
        try:
            from pxr import Usd, UsdGeom, UsdLux, Gf
        except ImportError:
            return
        
        self.stage = Usd.Stage.CreateInMemory()
        
        # 큐브
        cube = UsdGeom.Cube.Define(self.stage, '/World/Cube')
        cube.GetSizeAttr().Set(1.0)
        cube.AddTranslateOp().Set(Gf.Vec3d(-1.5, 0.5, 0))
        cube.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.5, 0.9)])
        
        # 구
        sphere = UsdGeom.Sphere.Define(self.stage, '/World/Sphere')
        sphere.GetRadiusAttr().Set(0.8)
        sphere.AddTranslateOp().Set(Gf.Vec3d(1.5, 0.8, 0))
        sphere.GetDisplayColorAttr().Set([Gf.Vec3f(0.9, 0.3, 0.2)])
        
        # 실린더
        cylinder = UsdGeom.Cylinder.Define(self.stage, '/World/Cylinder')
        cylinder.GetRadiusAttr().Set(0.5)
        cylinder.GetHeightAttr().Set(2.0)
        cylinder.AddTranslateOp().Set(Gf.Vec3d(0, 1, -2))
        cylinder.GetDisplayColorAttr().Set([Gf.Vec3f(0.3, 0.8, 0.3)])
        
        # 바닥
        plane = UsdGeom.Mesh.Define(self.stage, '/World/Ground')
        plane.GetPointsAttr().Set([
            Gf.Vec3f(-5, 0, -5), Gf.Vec3f(5, 0, -5),
            Gf.Vec3f(5, 0, 5), Gf.Vec3f(-5, 0, 5)
        ])
        plane.GetFaceVertexIndicesAttr().Set([0, 1, 2, 3])
        plane.GetFaceVertexCountsAttr().Set([4])
        plane.GetDisplayColorAttr().Set([Gf.Vec3f(0.4, 0.4, 0.45)])
        
        self.camera.frame_bounds([-5, 0, -5], [5, 3, 5])
        
        self.sceneLoaded.emit("Sample Scene")
        self.update()
    
    # 마우스 이벤트
    def mousePressEvent(self, event):
        self.camera.last_pos = event.position()
        
        if event.button() == Qt.MouseButton.LeftButton:
            self.camera.rotating = True
        elif event.button() == Qt.MouseButton.RightButton:
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
            self.camera.pan(dx, dy)
            self.update()
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.camera.zoom(delta)
        self.update()
    
    def keyPressEvent(self, event):
        key = event.key()
        
        if key == Qt.Key.Key_F:
            if self.stage:
                try:
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
                except:
                    pass
            self.update()
        
        elif key == Qt.Key.Key_G:
            self.show_grid = not self.show_grid
            self.update()
        
        elif key == Qt.Key.Key_A:
            self.show_axes = not self.show_axes
            self.update()
        
        elif key == Qt.Key.Key_W:
            modes = ['shaded', 'wireframe', 'points']
            idx = (modes.index(self.draw_mode) + 1) % len(modes)
            self.draw_mode = modes[idx]
            print(f"Draw mode: {self.draw_mode}")
            self.update()
        
        elif key == Qt.Key.Key_L:
            self.enable_lighting = not self.enable_lighting
            print(f"Lighting: {'ON' if self.enable_lighting else 'OFF'}")
            self.update()


class SceneHierarchyWidget(QDockWidget):
    """씬 계층 구조 패널"""
    
    primSelected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__("Scene Hierarchy", parent)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Prim", "Type"])
        self.tree.itemClicked.connect(self.on_item_clicked)
        
        self.setWidget(self.tree)
    
    def update_hierarchy(self, stage):
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
                item.setData(0, Qt.ItemDataRole.UserRole, str(child.GetPath()))
                add_children(item, child)
        
        root = stage.GetPseudoRoot()
        for child in root.GetChildren():
            item = QTreeWidgetItem([
                child.GetName(),
                child.GetTypeName()
            ])
            self.tree.addTopLevelItem(item)
            item.setData(0, Qt.ItemDataRole.UserRole, str(child.GetPath()))
            add_children(item, child)
        
        self.tree.expandAll()
    
    def on_item_clicked(self, item, column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.primSelected.emit(path)


class PropertiesWidget(QDockWidget):
    """속성 패널"""
    
    def __init__(self, parent=None):
        super().__init__("Properties", parent)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.info_label = QLabel("선택된 프림 없음")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        self.setWidget(widget)
    
    def show_prim_properties(self, stage, prim_path):
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


class USDViewer(QMainWindow):
    """USD 뷰어 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("USD Viewer (PyQt6)")
        self.setMinimumSize(1280, 720)
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        
        self.viewport.create_sample_stage()
        self.hierarchy.update_hierarchy(self.viewport.stage)
    
    def setup_ui(self):
        self.viewport = GLViewport()
        self.setCentralWidget(self.viewport)
        
        self.hierarchy = SceneHierarchyWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.hierarchy)
        
        self.properties = PropertiesWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.properties)
        
        self.hierarchy.primSelected.connect(self.on_prim_selected)
        self.viewport.sceneLoaded.connect(self.on_scene_loaded)
        
        self.statusBar().showMessage("준비")
    
    def setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open USD...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        view_menu = menubar.addMenu("View")
        
        frame_action = QAction("Frame All (F)", self)
        frame_action.triggered.connect(lambda: self.viewport.keyPressEvent(
            type('', (), {'key': lambda: Qt.Key.Key_F})()
        ))
        view_menu.addAction(frame_action)
    
    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        mode_label = QLabel(" Draw Mode: ")
        toolbar.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Shaded", "Wireframe", "Points"])
        self.mode_combo.currentTextChanged.connect(self.on_draw_mode_changed)
        toolbar.addWidget(self.mode_combo)
        
        toolbar.addSeparator()
        
        self.lighting_check = QCheckBox("Lighting")
        self.lighting_check.setChecked(True)
        self.lighting_check.stateChanged.connect(self.on_lighting_changed)
        toolbar.addWidget(self.lighting_check)
        
        toolbar.addSeparator()
        
        self.grid_check = QCheckBox("Grid")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(
            lambda s: setattr(self.viewport, 'show_grid', s == Qt.CheckState.Checked.value) or self.viewport.update()
        )
        toolbar.addWidget(self.grid_check)
        
        self.axes_check = QCheckBox("Axes")
        self.axes_check.setChecked(True)
        self.axes_check.stateChanged.connect(
            lambda s: setattr(self.viewport, 'show_axes', s == Qt.CheckState.Checked.value) or self.viewport.update()
        )
        toolbar.addWidget(self.axes_check)
    
    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open USD File", "",
            "USD Files (*.usd *.usda *.usdc *.usdz);;All Files (*)"
        )
        
        if filepath:
            if self.viewport.load_stage(filepath):
                self.hierarchy.update_hierarchy(self.viewport.stage)
    
    def on_scene_loaded(self, name):
        self.statusBar().showMessage(f"로드됨: {name}")
        self.setWindowTitle(f"USD Viewer - {Path(name).name if Path(name).exists() else name}")
    
    def on_prim_selected(self, prim_path):
        self.statusBar().showMessage(f"선택: {prim_path}")
        self.properties.show_prim_properties(self.viewport.stage, prim_path)
    
    def on_draw_mode_changed(self, text):
        mode_map = {"Shaded": "shaded", "Wireframe": "wireframe", "Points": "points"}
        self.viewport.draw_mode = mode_map.get(text, "shaded")
        self.viewport.update()
    
    def on_lighting_changed(self, state):
        self.viewport.enable_lighting = (state == Qt.CheckState.Checked.value)
        self.viewport.update()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    viewer = USDViewer()
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if Path(filepath).exists():
            viewer.viewport.load_stage(filepath)
            viewer.hierarchy.update_hierarchy(viewer.viewport.stage)
    
    viewer.show()
    
    print("""
=== USD Viewer (PyQt6) ===
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
==========================
""")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
