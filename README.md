# Unitree
Unitree


---

## USD 뷰어

## 요약
| 뷰어 | 특징 | 학습 포인트| 
|:----:|:----:|:----:|
| 기본 뷰어 | PyOpenGL + GLFW로 직접 렌더링 | 버텍스/메시 구조, OpenGL 파이프라인, 행렬 계산| 
| 중급 뷰어 | PySide6 + USD Hydra 렌더러 |  Hydra 프레임워크, Storm 렌더러, Qt GUI 통합 | 

```
# 의존성 설치
pip install numpy usd-core PyOpenGL PyOpenGL_accelerate glfw PySide6

# 샘플 USD 파일 생성
cd samples && python create_samples.py

# 기본 뷰어 실행
cd basic_viewer && python usd_basic_viewer.py

# 중급 뷰어 실행
cd hydra_viewer && python usd_hydra_viewer.py
```
