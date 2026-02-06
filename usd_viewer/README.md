# USD Python Viewers

Universal Scene Description (USD) 파일을 위한 Python 뷰어 프로젝트입니다.

## 📁 프로젝트 구조

```
usd_viewers/
├── basic_viewer/
│   └── usd_basic_viewer.py     # PyOpenGL 기반 기본 뷰어
├── hydra_viewer/
│   └── usd_hydra_viewer.py     # PySide6 + Hydra 기반 중급 뷰어
├── samples/
│   └── create_samples.py       # 테스트용 USD 파일 생성
└── README.md
```

## 🔧 설치

### 공통 의존성

```bash
pip install numpy usd-core
```

### 기본 뷰어 추가 의존성

```bash
pip install PyOpenGL PyOpenGL_accelerate glfw
```

### 중급 뷰어 추가 의존성

```bash
pip install PySide6 PyOpenGL PyOpenGL_accelerate
```

### 전체 설치 (한번에)

```bash
pip install numpy usd-core PyOpenGL PyOpenGL_accelerate glfw PySide6
```

## 🚀 실행

### 샘플 USD 파일 생성

```bash
cd samples
python create_samples.py
```

생성되는 파일:
- `simple_scene.usda` - 기본 도형들
- `mesh_scene.usda` - 커스텀 메시 (피라미드, 토러스)
- `hierarchy_scene.usda` - 계층 구조 (로봇 팔)
- `animated_scene.usda` - 애니메이션 (5초, 24fps)

### 기본 뷰어 실행

```bash
cd basic_viewer
python usd_basic_viewer.py                        # 샘플 지오메트리
python usd_basic_viewer.py ../samples/simple_scene.usda  # USD 파일 로드
```

### 중급 뷰어 실행

```bash
cd hydra_viewer
python usd_hydra_viewer.py                        # 샘플 씬
python usd_hydra_viewer.py ../samples/hierarchy_scene.usda  # USD 파일 로드
```

## 🎮 조작법

### 마우스

| 동작 | 기본 뷰어 | 중급 뷰어 |
|------|----------|----------|
| 회전 | 좌클릭 드래그 | 좌클릭 드래그 |
| 패닝 | 우클릭 드래그 | 우클릭 드래그 |
| 줌 | 휠 스크롤 | 휠 스크롤 |

### 키보드

| 키 | 기본 뷰어 | 중급 뷰어 |
|----|----------|----------|
| W | 와이어프레임 토글 | 드로우 모드 순환 |
| G | 그리드 토글 | 그리드 토글 |
| A | 좌표축 토글 | 좌표축 토글 |
| R | 카메라 리셋 | - |
| F | - | 씬 프레임 맞춤 |
| L | - | 조명 토글 |
| H | 도움말 | - |
| Q/ESC | 종료 | - |

## 📊 뷰어 비교

| 기능 | 기본 뷰어 | 중급 뷰어 |
|------|----------|----------|
| **렌더링 엔진** | 직접 OpenGL | USD Hydra (Storm) |
| **GUI** | GLFW (최소) | PySide6 (풀 GUI) |
| **머티리얼** | DisplayColor만 | PBR 지원 |
| **조명** | 기본 OpenGL | USD 조명 시스템 |
| **씬 탐색** | 없음 | 계층 구조 트리 |
| **코드 복잡도** | ~500줄 | ~800줄 |
| **학습 목표** | OpenGL 렌더링 기초 | USD 생태계 이해 |

## 📚 학습 순서 권장

### 1단계: 기본 뷰어로 핵심 개념 이해

```
렌더링 파이프라인 직접 구현
├── 버텍스, 페이스, 노멀 데이터 구조
├── OpenGL 상태 머신
├── 투영/뷰 행렬 계산
└── 마우스 기반 카메라 제어
```

**핵심 학습 포인트:**
- USD 파일에서 메시 데이터 추출 (`UsdGeom.Mesh`)
- 삼각형 분할 (Triangulation)
- 노멀 계산 및 조명
- 바운딩 박스 기반 카메라 초기화

### 2단계: 중급 뷰어로 USD 생태계 이해

```
Hydra 렌더링 프레임워크
├── UsdImagingGL.Engine
├── Storm 렌더 델리게이트
├── 렌더 파라미터 시스템
└── 시간 샘플 (애니메이션)
```

**핵심 학습 포인트:**
- Hydra가 "왜" 필요한지 이해 (복잡한 씬 최적화)
- 렌더 델리게이트 개념 (Storm, Embree, etc.)
- USD 스테이지 구조 및 계층 탐색
- Qt 통합 방법

## 🔍 코드 하이라이트

### USD 메시 데이터 추출 (기본 뷰어)

```python
def extract_mesh_from_prim(prim):
    usd_mesh = UsdGeom.Mesh(prim)
    
    # 버텍스
    points = usd_mesh.GetPointsAttr().Get()
    
    # 페이스 인덱스
    indices = usd_mesh.GetFaceVertexIndicesAttr().Get()
    counts = usd_mesh.GetFaceVertexCountsAttr().Get()
    
    # 삼각형화
    for count in counts:
        for i in range(1, count - 1):
            triangle = [indices[0], indices[i], indices[i+1]]
```

### Hydra 렌더링 (중급 뷰어)

```python
def render_hydra(self):
    params = UsdImagingGL.RenderParams()
    params.frame = Usd.TimeCode(self.time_code)
    params.drawMode = UsdImagingGL.DrawMode.DRAW_SHADED_SMOOTH
    params.enableLighting = True
    
    self.renderer.SetCameraState(view_matrix, proj_matrix)
    self.renderer.Render(root, params)
```

## 🔗 관련 자료

- [USD 공식 문서](https://openusd.org/docs/)
- [Pixar USD GitHub](https://github.com/PixarAnimationStudios/USD)
- [Hydra 아키텍처](https://openusd.org/docs/api/hd_page_front.html)
- [NVIDIA Omniverse](https://developer.nvidia.com/omniverse)

## 📝 향후 확장 아이디어

1. **멀티 렌더 델리게이트 지원** - Embree, RenderMan 등
2. **USD Composer 스타일 편집** - 프림 생성/수정/삭제
3. **USDZ 내보내기** - AR 콘텐츠 제작
4. **물리 시뮬레이션 미리보기** - UsdPhysics 통합
5. **Python 스크립팅 콘솔** - 런타임 USD 조작

## ⚠️ 알려진 제한사항

- 기본 뷰어는 텍스처 지원 없음
- Hydra Storm은 일부 고급 PBR 기능 미지원
- 대용량 씬 (100만+ 폴리곤)에서 성능 저하 가능
- Windows에서 OpenGL 드라이버 호환성 이슈 가능

## 📜 라이선스

이 프로젝트는 교육 목적으로 제작되었습니다.
