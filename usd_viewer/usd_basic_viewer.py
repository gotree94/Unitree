"""
USD Basic Viewer - PyOpenGL 기반 기본 뷰어
==========================================

학습 목표:
- USD 파일에서 메시 데이터 추출 방법 이해
- OpenGL 렌더링 파이프라인 직접 구현
- 카메라 컨트롤 (회전, 줌, 패닝) 구현

의존성:
    pip install PyOpenGL PyOpenGL_accelerate glfw numpy usd-core

사용법:
    python usd_basic_viewer.py [usd_file_path]
    python usd_basic_viewer.py  # 샘플 큐브 생성
"""

import sys
import math
import numpy as np
from pathlib import Path

try:
    import glfw
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print("필요한 패키지를 설치하세요:")
    print("  pip install PyOpenGL PyOpenGL_accelerate glfw numpy")
    sys.exit(1)

try:
    from pxr import Usd, UsdGeom, Gf
    USD_AVAILABLE = True
except ImportError:
    USD_AVAILABLE = False
    print("경고: USD 라이브러리가 없습니다. 샘플 지오메트리만 사용 가능합니다.")
    print("  pip install usd-core")


class Camera:
    """마우스로 제어 가능한 Orbit 카메라"""
    
    def __init__(self):
        self.distance = 5.0      # 타겟으로부터의 거리
        self.azimuth = 45.0      # 수평 회전각 (도)
        self.elevation = 30.0    # 수직 회전각 (도)
        self.target = [0.0, 0.0, 0.0]  # 바라보는 지점
        
        # 마우스 상태
        self.last_x = 0
        self.last_y = 0
        self.rotating = False
        self.panning = False
        self.zooming = False
    
    def apply(self):
        """OpenGL 뷰 행렬 적용"""
        glLoadIdentity()
        
        # 카메라 위치 계산 (구면 좌표계)
        az_rad = math.radians(self.azimuth)
        el_rad = math.radians(self.elevation)
        
        eye_x = self.target[0] + self.distance * math.cos(el_rad) * math.sin(az_rad)
        eye_y = self.target[1] + self.distance * math.sin(el_rad)
        eye_z = self.target[2] + self.distance * math.cos(el_rad) * math.cos(az_rad)
        
        gluLookAt(
            eye_x, eye_y, eye_z,           # 카메라 위치
            self.target[0], self.target[1], self.target[2],  # 타겟
            0.0, 1.0, 0.0                   # 업 벡터
        )
    
    def rotate(self, dx, dy):
        """마우스 드래그로 회전"""
        self.azimuth -= dx * 0.5
        self.elevation += dy * 0.5
        self.elevation = max(-89, min(89, self.elevation))
    
    def pan(self, dx, dy):
        """마우스 드래그로 패닝"""
        scale = self.distance * 0.002
        
        az_rad = math.radians(self.azimuth)
        right = [math.cos(az_rad), 0, -math.sin(az_rad)]
        up = [0, 1, 0]
        
        self.target[0] -= right[0] * dx * scale
        self.target[2] -= right[2] * dx * scale
        self.target[1] += dy * scale
    
    def zoom(self, delta):
        """마우스 휠로 줌"""
        self.distance *= (1.0 - delta * 0.1)
        self.distance = max(0.1, min(100.0, self.distance))


class Mesh:
    """메시 데이터를 저장하고 렌더링하는 클래스"""
    
    def __init__(self, name="mesh"):
        self.name = name
        self.vertices = []      # [[x, y, z], ...]
        self.normals = []       # [[nx, ny, nz], ...]
        self.faces = []         # [[v0, v1, v2], ...] 삼각형 인덱스
        self.color = [0.7, 0.7, 0.8]  # 기본 색상
        self.transform = np.eye(4)     # 변환 행렬
    
    def compute_normals(self):
        """페이스 노멀 계산 (플랫 셰이딩용)"""
        self.normals = []
        vertices = np.array(self.vertices)
        
        for face in self.faces:
            if len(face) >= 3:
                v0 = vertices[face[0]]
                v1 = vertices[face[1]]
                v2 = vertices[face[2]]
                
                edge1 = v1 - v0
                edge2 = v2 - v0
                normal = np.cross(edge1, edge2)
                
                length = np.linalg.norm(normal)
                if length > 0:
                    normal = normal / length
                else:
                    normal = np.array([0, 1, 0])
                
                self.normals.append(normal)
    
    def get_bounds(self):
        """바운딩 박스 반환"""
        if not self.vertices:
            return [0, 0, 0], [1, 1, 1]
        
        vertices = np.array(self.vertices)
        min_bound = vertices.min(axis=0)
        max_bound = vertices.max(axis=0)
        return min_bound.tolist(), max_bound.tolist()
    
    def render(self, wireframe=False):
        """OpenGL로 메시 렌더링"""
        glPushMatrix()
        glMultMatrixf(self.transform.T.flatten())
        
        if wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glColor3f(0.2, 0.2, 0.2)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glColor3f(*self.color)
        
        glBegin(GL_TRIANGLES)
        for i, face in enumerate(self.faces):
            if i < len(self.normals):
                glNormal3fv(self.normals[i])
            
            for vertex_idx in face[:3]:  # 삼각형만 처리
                if vertex_idx < len(self.vertices):
                    glVertex3fv(self.vertices[vertex_idx])
        glEnd()
        
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glPopMatrix()


def create_sample_cube():
    """샘플 큐브 메시 생성"""
    mesh = Mesh("sample_cube")
    
    # 큐브 버텍스 (단위 큐브, 중심이 원점)
    mesh.vertices = [
        [-0.5, -0.5, -0.5], [0.5, -0.5, -0.5],
        [0.5, 0.5, -0.5], [-0.5, 0.5, -0.5],
        [-0.5, -0.5, 0.5], [0.5, -0.5, 0.5],
        [0.5, 0.5, 0.5], [-0.5, 0.5, 0.5]
    ]
    
    # 큐브 페이스 (삼각형으로 분할)
    mesh.faces = [
        [0, 1, 2], [0, 2, 3],  # 뒤
        [4, 6, 5], [4, 7, 6],  # 앞
        [0, 4, 5], [0, 5, 1],  # 아래
        [2, 6, 7], [2, 7, 3],  # 위
        [0, 3, 7], [0, 7, 4],  # 왼쪽
        [1, 5, 6], [1, 6, 2],  # 오른쪽
    ]
    
    mesh.color = [0.3, 0.6, 0.9]
    mesh.compute_normals()
    return mesh


def create_sample_sphere(radius=1.0, segments=16, rings=12):
    """샘플 구 메시 생성"""
    mesh = Mesh("sample_sphere")
    
    # 버텍스 생성
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2.0 * math.pi * j / segments
            
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            
            mesh.vertices.append([x, y, z])
    
    # 페이스 생성
    for i in range(rings):
        for j in range(segments):
            next_j = (j + 1) % segments
            
            v0 = i * segments + j
            v1 = i * segments + next_j
            v2 = (i + 1) * segments + next_j
            v3 = (i + 1) * segments + j
            
            mesh.faces.append([v0, v2, v1])
            mesh.faces.append([v0, v3, v2])
    
    mesh.color = [0.9, 0.5, 0.3]
    mesh.compute_normals()
    return mesh


def load_usd_file(filepath):
    """USD 파일에서 메시 로드"""
    if not USD_AVAILABLE:
        print("USD 라이브러리가 없어 샘플 지오메트리를 사용합니다.")
        return [create_sample_cube(), create_sample_sphere()]
    
    meshes = []
    
    try:
        stage = Usd.Stage.Open(filepath)
        if not stage:
            print(f"USD 파일을 열 수 없습니다: {filepath}")
            return [create_sample_cube()]
        
        print(f"USD 파일 로드: {filepath}")
        
        # 모든 메시 프림 순회
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                mesh = extract_mesh_from_prim(prim)
                if mesh:
                    meshes.append(mesh)
                    print(f"  메시 발견: {prim.GetPath()}")
        
        if not meshes:
            print("메시를 찾을 수 없습니다. 샘플 큐브를 사용합니다.")
            return [create_sample_cube()]
        
        print(f"총 {len(meshes)}개의 메시 로드 완료")
        
    except Exception as e:
        print(f"USD 로드 오류: {e}")
        return [create_sample_cube()]
    
    return meshes


def extract_mesh_from_prim(prim):
    """USD Mesh Prim에서 메시 데이터 추출"""
    mesh = Mesh(str(prim.GetPath()))
    
    usd_mesh = UsdGeom.Mesh(prim)
    
    # 포인트 (버텍스) 추출
    points_attr = usd_mesh.GetPointsAttr()
    if points_attr:
        points = points_attr.Get()
        if points:
            mesh.vertices = [[p[0], p[1], p[2]] for p in points]
    
    # 페이스 버텍스 인덱스 추출
    face_indices_attr = usd_mesh.GetFaceVertexIndicesAttr()
    face_counts_attr = usd_mesh.GetFaceVertexCountsAttr()
    
    if face_indices_attr and face_counts_attr:
        indices = face_indices_attr.Get()
        counts = face_counts_attr.Get()
        
        if indices and counts:
            idx = 0
            for count in counts:
                face = []
                for _ in range(count):
                    if idx < len(indices):
                        face.append(indices[idx])
                        idx += 1
                
                # 삼각형화 (팬 방식)
                if len(face) >= 3:
                    for i in range(1, len(face) - 1):
                        mesh.faces.append([face[0], face[i], face[i + 1]])
    
    # 월드 변환 행렬 가져오기
    xformable = UsdGeom.Xformable(prim)
    world_transform = xformable.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    mesh.transform = np.array(world_transform).T
    
    # 색상 추출 시도
    display_color_attr = usd_mesh.GetDisplayColorAttr()
    if display_color_attr:
        colors = display_color_attr.Get()
        if colors and len(colors) > 0:
            mesh.color = [colors[0][0], colors[0][1], colors[0][2]]
    
    mesh.compute_normals()
    return mesh


class USDBasicViewer:
    """USD 기본 뷰어 메인 클래스"""
    
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.window = None
        self.camera = Camera()
        self.meshes = []
        
        # 렌더링 옵션
        self.show_wireframe = False
        self.show_axes = True
        self.show_grid = True
        
        # 조명 설정
        self.light_position = [5.0, 10.0, 5.0, 1.0]
    
    def init_glfw(self):
        """GLFW 초기화"""
        if not glfw.init():
            raise RuntimeError("GLFW 초기화 실패")
        
        # OpenGL 버전 힌트
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 2)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
        glfw.window_hint(glfw.SAMPLES, 4)  # 안티앨리어싱
        
        self.window = glfw.create_window(
            self.width, self.height, 
            "USD Basic Viewer - PyOpenGL", 
            None, None
        )
        
        if not self.window:
            glfw.terminate()
            raise RuntimeError("GLFW 윈도우 생성 실패")
        
        glfw.make_context_current(self.window)
        glfw.swap_interval(1)  # VSync
        
        # 콜백 설정
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        glfw.set_cursor_pos_callback(self.window, self.cursor_pos_callback)
        glfw.set_scroll_callback(self.window, self.scroll_callback)
        glfw.set_key_callback(self.window, self.key_callback)
        glfw.set_framebuffer_size_callback(self.window, self.resize_callback)
    
    def init_opengl(self):
        """OpenGL 초기화"""
        glClearColor(0.15, 0.15, 0.18, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_MULTISAMPLE)
        
        # 조명 설정
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        
        # 머티리얼 설정
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # 프로젝션 설정
        self.setup_projection()
    
    def setup_projection(self):
        """투영 행렬 설정"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.width / self.height if self.height > 0 else 1.0
        gluPerspective(45.0, aspect, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
    
    def load_meshes(self, filepath=None):
        """메시 로드 및 카메라 조정"""
        if filepath and Path(filepath).exists():
            self.meshes = load_usd_file(filepath)
        else:
            print("샘플 지오메트리를 생성합니다.")
            self.meshes = [create_sample_cube(), create_sample_sphere()]
            # 구를 옆으로 이동
            self.meshes[1].transform[3, 0] = 2.0
        
        # 전체 씬의 바운딩 박스 계산
        self.fit_camera_to_scene()
    
    def fit_camera_to_scene(self):
        """씬에 맞게 카메라 조정"""
        if not self.meshes:
            return
        
        all_min = [float('inf')] * 3
        all_max = [float('-inf')] * 3
        
        for mesh in self.meshes:
            min_b, max_b = mesh.get_bounds()
            for i in range(3):
                all_min[i] = min(all_min[i], min_b[i])
                all_max[i] = max(all_max[i], max_b[i])
        
        # 중심과 크기 계산
        center = [(all_min[i] + all_max[i]) / 2 for i in range(3)]
        size = max(all_max[i] - all_min[i] for i in range(3))
        
        self.camera.target = center
        self.camera.distance = size * 2.0
    
    def draw_grid(self, size=10, divisions=10):
        """바닥 그리드 렌더링"""
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.3, 0.3)
        
        step = size / divisions
        half = size / 2
        
        glBegin(GL_LINES)
        for i in range(divisions + 1):
            pos = -half + i * step
            # X 방향 선
            glVertex3f(-half, 0, pos)
            glVertex3f(half, 0, pos)
            # Z 방향 선
            glVertex3f(pos, 0, -half)
            glVertex3f(pos, 0, half)
        glEnd()
        
        glEnable(GL_LIGHTING)
    
    def draw_axes(self, length=1.0):
        """좌표축 렌더링"""
        glDisable(GL_LIGHTING)
        glLineWidth(2.0)
        
        glBegin(GL_LINES)
        # X축 (빨강)
        glColor3f(1.0, 0.2, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)
        # Y축 (초록)
        glColor3f(0.2, 1.0, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)
        # Z축 (파랑)
        glColor3f(0.2, 0.2, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)
        glEnd()
        
        glLineWidth(1.0)
        glEnable(GL_LIGHTING)
    
    def render(self):
        """메인 렌더링"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # 카메라 적용
        self.camera.apply()
        
        # 조명 위치 업데이트
        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)
        
        # 보조 요소 렌더링
        if self.show_grid:
            self.draw_grid()
        if self.show_axes:
            self.draw_axes()
        
        # 메시 렌더링
        for mesh in self.meshes:
            mesh.render(wireframe=False)
            if self.show_wireframe:
                mesh.render(wireframe=True)
    
    # === 콜백 함수들 ===
    
    def mouse_button_callback(self, window, button, action, mods):
        x, y = glfw.get_cursor_pos(window)
        
        if action == glfw.PRESS:
            self.camera.last_x = x
            self.camera.last_y = y
            
            if button == glfw.MOUSE_BUTTON_LEFT:
                self.camera.rotating = True
            elif button == glfw.MOUSE_BUTTON_RIGHT:
                self.camera.panning = True
            elif button == glfw.MOUSE_BUTTON_MIDDLE:
                self.camera.zooming = True
        
        elif action == glfw.RELEASE:
            self.camera.rotating = False
            self.camera.panning = False
            self.camera.zooming = False
    
    def cursor_pos_callback(self, window, x, y):
        dx = x - self.camera.last_x
        dy = y - self.camera.last_y
        self.camera.last_x = x
        self.camera.last_y = y
        
        if self.camera.rotating:
            self.camera.rotate(dx, dy)
        elif self.camera.panning:
            self.camera.pan(dx, dy)
        elif self.camera.zooming:
            self.camera.zoom(dy * 0.1)
    
    def scroll_callback(self, window, xoffset, yoffset):
        self.camera.zoom(yoffset)
    
    def key_callback(self, window, key, scancode, action, mods):
        if action != glfw.PRESS:
            return
        
        if key == glfw.KEY_ESCAPE or key == glfw.KEY_Q:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_W:
            self.show_wireframe = not self.show_wireframe
            print(f"와이어프레임: {'ON' if self.show_wireframe else 'OFF'}")
        elif key == glfw.KEY_G:
            self.show_grid = not self.show_grid
            print(f"그리드: {'ON' if self.show_grid else 'OFF'}")
        elif key == glfw.KEY_A:
            self.show_axes = not self.show_axes
            print(f"좌표축: {'ON' if self.show_axes else 'OFF'}")
        elif key == glfw.KEY_R:
            self.camera = Camera()
            self.fit_camera_to_scene()
            print("카메라 리셋")
        elif key == glfw.KEY_H:
            self.print_help()
    
    def resize_callback(self, window, width, height):
        self.width = width
        self.height = height
        glViewport(0, 0, width, height)
        self.setup_projection()
    
    def print_help(self):
        """도움말 출력"""
        print("""
=== USD Basic Viewer 조작법 ===
  마우스:
    좌클릭 드래그  : 회전
    우클릭 드래그  : 패닝
    휠             : 줌

  키보드:
    W : 와이어프레임 토글
    G : 그리드 토글
    A : 좌표축 토글
    R : 카메라 리셋
    H : 도움말
    Q/ESC : 종료
================================
""")
    
    def run(self, filepath=None):
        """메인 루프"""
        self.init_glfw()
        self.init_opengl()
        self.load_meshes(filepath)
        
        print("\n=== USD Basic Viewer 시작 ===")
        print("H 키로 도움말을 볼 수 있습니다.\n")
        
        while not glfw.window_should_close(self.window):
            self.render()
            glfw.swap_buffers(self.window)
            glfw.poll_events()
        
        glfw.terminate()
        print("\n뷰어 종료")


def main():
    """메인 함수"""
    viewer = USDBasicViewer()
    
    filepath = None
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not Path(filepath).exists():
            print(f"파일을 찾을 수 없습니다: {filepath}")
            filepath = None
    
    viewer.run(filepath)


if __name__ == "__main__":
    main()
