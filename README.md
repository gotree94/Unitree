# Unitree

https://github.com/unitreerobotics

https://github.com/orgs/unitreerobotics/repositories

https://github.com/unitreerobotics/unitree_ros/tree/master/robots/h1_description

---

# USD Python Viewers

Universal Scene Description (USD) 파일을 위한 Python 뷰어 프로젝트입니다.

## 📁 프로젝트 구조

```
usd_viewers/
├── basic_viewer/
│   └── usd_basic_viewer.py     # PyOpenGL + GLFW 기반 기본 뷰어
├── hydra_viewer/
│   ├── usd_hydra_viewer.py     # PySide6 + Hydra 기반 중급 뷰어
│   └── usd_hydra_viewer_pyqt6.py  # PyQt6 버전 (PySide6 DLL 충돌 시)
├── samples/
│   └── create_samples.py       # 테스트용 USD 파일 생성
└── README.md
```

## 🔧 설치

### 권장: 새 Conda 환경 생성

Anaconda base 환경에서 PySide6 DLL 충돌이 발생할 수 있으므로 새 환경을 권장합니다.

```bash
# 새 환경 생성
conda create -n usd_viewer python=3.11 -y

# 환경 활성화
conda activate usd_viewer

# 전체 패키지 설치
pip install numpy usd-core PyOpenGL PyOpenGL_accelerate glfw PySide6
```

### 패키지별 설치

```bash
# 공통 (필수)
pip install numpy usd-core

# 기본 뷰어용
pip install PyOpenGL PyOpenGL_accelerate glfw

# 중급 뷰어용 (PySide6 또는 PyQt6 중 하나 선택)
pip install PySide6
# 또는 PySide6 DLL 충돌 시
pip install PyQt6
```

## 🚀 실행

### ⚠️ 중요: USD 파일 경로

USD 파일은 **상대 경로**로 다른 파일들을 참조합니다. 따라서 **USD 파일이 있는 폴더에서 실행**해야 합니다.

### Unitree 로봇 모델 실행 예시

```bash
# 환경 활성화
conda activate usd_viewer

# === Go2 로봇 ===
cd C:\Users\Administrator\Desktop\Robot\Unitree\Unitree_model\Go2\usd
python C:\Users\Administrator\Desktop\Robot\Unitree\usd_viewer\usd_basic_viewer.py go2.usd

# === G1 로봇 (29dof) ===
cd C:\Users\Administrator\Desktop\Robot\Unitree\Unitree_model\G1\29dof\usd\g1_29dof_rev_1_0
python C:\Users\Administrator\Desktop\Robot\Unitree\usd_viewer\usd_basic_viewer.py g1_29dof_rev_1_0.usd

# === H1 로봇 ===
cd C:\Users\Administrator\Desktop\Robot\Unitree\Unitree_model\H1\h1\usd
python C:\Users\Administrator\Desktop\Robot\Unitree\usd_viewer\usd_basic_viewer.py h1.usd

# === B2 로봇 ===
cd C:\Users\Administrator\Desktop\Robot\Unitree\Unitree_model\B2\usd
python C:\Users\Administrator\Desktop\Robot\Unitree\usd_viewer\usd_basic_viewer.py B2.usd
```

### 일반 USD 파일 실행

```bash
# 샘플 지오메트리로 테스트 (USD 파일 없이)
python usd_basic_viewer.py

# USD 파일 지정
python usd_basic_viewer.py path/to/your/file.usd
```

### 중급 뷰어 실행

```bash
# PySide6 버전
python usd_hydra_viewer.py go2.usd

# PyQt6 버전 (PySide6 DLL 충돌 시)
python usd_hydra_viewer_pyqt6.py go2.usd
```

## 🎮 조작법

### 마우스

| 동작 | 기능 |
|------|------|
| 좌클릭 드래그 | 회전 (Orbit) |
| 우클릭 드래그 | 패닝 (Pan) |
| 중클릭 드래그 | 줌 |
| 휠 스크롤 | 줌 |

### 키보드

| 키 | 기능 |
|----|------|
| **W** | 드로우 모드 순환 (Shaded → Wireframe → Points) |
| **G** | 그리드 토글 |
| **A** | 좌표축 토글 |
| **L** | 조명 토글 |
| **F** | 씬에 맞게 카메라 프레임 |
| **R** | 카메라 리셋 |
| **H** | 도움말 출력 |
| **Q / ESC** | 종료 |

## 📊 뷰어 비교

| 기능 | 기본 뷰어 | 중급 뷰어 |
|------|----------|----------|
| **파일** | `usd_basic_viewer.py` | `usd_hydra_viewer.py` |
| **렌더링** | 직접 OpenGL | USD Hydra (Storm) |
| **GUI** | GLFW (최소) | PySide6/PyQt6 (풀 GUI) |
| **Qt 필요** | ❌ 불필요 | ✅ 필요 |
| **씬 계층 트리** | ❌ | ✅ |
| **속성 패널** | ❌ | ✅ |
| **지원 도형** | Mesh, Cube, Sphere, Cylinder, Cone, Capsule | 전체 USD 프림 |
| **코드 복잡도** | ~700줄 | ~900줄 |
| **학습 목표** | OpenGL 렌더링 기초 | USD Hydra 생태계 |

## 🔧 문제 해결

### PySide6 DLL 충돌 (Anaconda base 환경)

```
ImportError: DLL load failed while importing QtWidgets
```

**해결책 1**: 새 Conda 환경 생성 (권장)
```bash
conda create -n usd_viewer python=3.11 -y
conda activate usd_viewer
pip install numpy usd-core PyOpenGL PyOpenGL_accelerate glfw PySide6
```

**해결책 2**: PyQt6 사용
```bash
pip install PyQt6
python usd_hydra_viewer_pyqt6.py go2.usd
```

**해결책 3**: 기본 뷰어 사용 (Qt 불필요)
```bash
python usd_basic_viewer.py go2.usd
```

### USD 파일 로드 실패

```
Could not open asset @configuration/xxx.usd@ for payload
```

**원인**: USD 파일이 상대 경로로 다른 파일을 참조하는데, 현재 디렉토리가 다름

**해결책**: USD 파일이 있는 폴더로 이동 후 실행
```bash
cd path/to/usd/folder
python /path/to/usd_basic_viewer.py file.usd
```

### 메시를 찾을 수 없음

```
메시를 찾을 수 없습니다. 샘플 큐브를 사용합니다.
```

**원인**: 
1. USD 파일에 메시가 없고 Reference/Payload로 외부 파일 참조
2. 참조된 파일들을 찾을 수 없음

**해결책**: USD 파일이 있는 디렉토리에서 실행

## 📚 학습 순서

### 1단계: 기본 뷰어로 핵심 개념 이해

```
OpenGL 렌더링 파이프라인 직접 구현
├── 버텍스, 페이스, 노멀 데이터 구조
├── 투영/뷰 행렬 계산
├── 조명 및 머티리얼
└── 마우스 기반 카메라 제어
```

### 2단계: 중급 뷰어로 USD 생태계 이해

```
Hydra 렌더링 프레임워크
├── UsdImagingGL.Engine
├── Storm 렌더 델리게이트
├── 렌더 파라미터 시스템
└── Qt GUI 통합
```

## 🔍 코드 하이라이트

### USD 메시 데이터 추출

```python
def extract_mesh(prim):
    usd_mesh = UsdGeom.Mesh(prim)
    
    # 버텍스
    points = usd_mesh.GetPointsAttr().Get()
    
    # 페이스 인덱스  
    indices = usd_mesh.GetFaceVertexIndicesAttr().Get()
    counts = usd_mesh.GetFaceVertexCountsAttr().Get()
    
    # 삼각형화 (Fan 방식)
    for count in counts:
        for i in range(1, count - 1):
            triangle = [face[0], face[i], face[i+1]]
```

### 기본 도형 렌더링

```python
# USD 기본 도형 지원
if prim.IsA(UsdGeom.Cube):
    size = UsdGeom.Cube(prim).GetSizeAttr().Get()
    PrimitiveRenderer.render_cube(size, color)

elif prim.IsA(UsdGeom.Sphere):
    radius = UsdGeom.Sphere(prim).GetRadiusAttr().Get()
    PrimitiveRenderer.render_sphere(radius, color)
```

## 🔗 관련 자료

- [OpenUSD 공식 문서](https://openusd.org/docs/)
- [Pixar USD GitHub](https://github.com/PixarAnimationStudios/USD)
- [Unitree Robotics](https://github.com/unitreerobotics)
- [NVIDIA Isaac Sim](https://developer.nvidia.com/isaac-sim)

## 📝 Unitree 모델 구조

```
Unitree_model/
├── Go2/usd/
│   ├── go2.usd                    # 메인 파일
│   └── configuration/
│       ├── go2_description_base.usd
│       ├── go2_description_physics.usd
│       └── go2_description_sensor.usd
│
├── G1/29dof/usd/g1_29dof_rev_1_0/
│   ├── g1_29dof_rev_1_0.usd       # 메인 파일
│   └── configuration/
│
├── H1/h1/usd/
│   ├── h1.usd                     # 메인 파일
│   └── configuration/
│
└── B2/usd/
    └── B2.usd                     # 메인 파일
```

## ⚠️ 알려진 제한사항

- 텍스처/머티리얼 렌더링 미지원 (기본 뷰어)
- Reference/Payload가 있는 USD는 해당 폴더에서 실행 필요
- 대용량 씬 (100만+ 폴리곤)에서 성능 저하 가능
- Hydra Storm은 일부 고급 PBR 기능 미지원

## 📜 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.
