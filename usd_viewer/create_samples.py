"""
샘플 USD 파일 생성 스크립트
===========================

뷰어 테스트를 위한 다양한 샘플 USD 파일을 생성합니다.
"""

import sys
import math

try:
    from pxr import Usd, UsdGeom, UsdLux, UsdShade, Sdf, Gf
except ImportError:
    print("USD 라이브러리가 필요합니다:")
    print("  pip install usd-core")
    sys.exit(1)


def create_simple_scene(filepath="simple_scene.usda"):
    """간단한 기본 도형 씬"""
    stage = Usd.Stage.CreateNew(filepath)
    
    # 루트 Xform
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    world = UsdGeom.Xform.Define(stage, '/World')
    
    # 큐브
    cube = UsdGeom.Cube.Define(stage, '/World/Cube')
    cube.GetSizeAttr().Set(2.0)
    cube.AddTranslateOp().Set(Gf.Vec3d(-3, 1, 0))
    cube.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.4, 0.8)])
    
    # 구
    sphere = UsdGeom.Sphere.Define(stage, '/World/Sphere')
    sphere.GetRadiusAttr().Set(1.2)
    sphere.AddTranslateOp().Set(Gf.Vec3d(0, 1.2, 0))
    sphere.GetDisplayColorAttr().Set([Gf.Vec3f(0.8, 0.3, 0.2)])
    
    # 실린더
    cylinder = UsdGeom.Cylinder.Define(stage, '/World/Cylinder')
    cylinder.GetRadiusAttr().Set(0.8)
    cylinder.GetHeightAttr().Set(3.0)
    cylinder.AddTranslateOp().Set(Gf.Vec3d(3, 1.5, 0))
    cylinder.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.7, 0.3)])
    
    # 콘
    cone = UsdGeom.Cone.Define(stage, '/World/Cone')
    cone.GetRadiusAttr().Set(1.0)
    cone.GetHeightAttr().Set(2.0)
    cone.AddTranslateOp().Set(Gf.Vec3d(0, 1, 3))
    cone.GetDisplayColorAttr().Set([Gf.Vec3f(0.9, 0.7, 0.1)])
    
    # 바닥 평면
    ground = UsdGeom.Mesh.Define(stage, '/World/Ground')
    ground.GetPointsAttr().Set([
        Gf.Vec3f(-10, 0, -10),
        Gf.Vec3f(10, 0, -10),
        Gf.Vec3f(10, 0, 10),
        Gf.Vec3f(-10, 0, 10)
    ])
    ground.GetFaceVertexIndicesAttr().Set([0, 1, 2, 3])
    ground.GetFaceVertexCountsAttr().Set([4])
    ground.GetDisplayColorAttr().Set([Gf.Vec3f(0.4, 0.4, 0.45)])
    
    # 조명
    light = UsdLux.DistantLight.Define(stage, '/World/Sun')
    light.GetIntensityAttr().Set(1.5)
    light.AddRotateXYZOp().Set(Gf.Vec3f(-45, 30, 0))
    
    stage.GetRootLayer().Save()
    print(f"생성됨: {filepath}")
    return filepath


def create_mesh_scene(filepath="mesh_scene.usda"):
    """커스텀 메시가 포함된 씬"""
    stage = Usd.Stage.CreateNew(filepath)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    
    # 피라미드 메시
    pyramid = UsdGeom.Mesh.Define(stage, '/World/Pyramid')
    
    # 피라미드 버텍스 (바닥 4점 + 꼭대기 1점)
    points = [
        Gf.Vec3f(-1, 0, -1),  # 0: 좌하
        Gf.Vec3f(1, 0, -1),   # 1: 우하
        Gf.Vec3f(1, 0, 1),    # 2: 우상
        Gf.Vec3f(-1, 0, 1),   # 3: 좌상
        Gf.Vec3f(0, 2, 0)     # 4: 꼭대기
    ]
    pyramid.GetPointsAttr().Set(points)
    
    # 페이스 (바닥 1개 + 옆면 4개)
    pyramid.GetFaceVertexIndicesAttr().Set([
        0, 1, 2, 3,  # 바닥
        0, 1, 4,     # 앞
        1, 2, 4,     # 오른쪽
        2, 3, 4,     # 뒤
        3, 0, 4      # 왼쪽
    ])
    pyramid.GetFaceVertexCountsAttr().Set([4, 3, 3, 3, 3])
    pyramid.AddTranslateOp().Set(Gf.Vec3d(-3, 0, 0))
    pyramid.GetDisplayColorAttr().Set([Gf.Vec3f(0.9, 0.7, 0.2)])
    
    # 토러스 (도넛) 메시
    torus = UsdGeom.Mesh.Define(stage, '/World/Torus')
    
    major_radius = 1.5
    minor_radius = 0.5
    major_segments = 24
    minor_segments = 12
    
    torus_points = []
    torus_indices = []
    torus_counts = []
    
    for i in range(major_segments):
        theta = 2 * math.pi * i / major_segments
        for j in range(minor_segments):
            phi = 2 * math.pi * j / minor_segments
            
            x = (major_radius + minor_radius * math.cos(phi)) * math.cos(theta)
            y = minor_radius * math.sin(phi)
            z = (major_radius + minor_radius * math.cos(phi)) * math.sin(theta)
            
            torus_points.append(Gf.Vec3f(x, y, z))
    
    for i in range(major_segments):
        next_i = (i + 1) % major_segments
        for j in range(minor_segments):
            next_j = (j + 1) % minor_segments
            
            v0 = i * minor_segments + j
            v1 = i * minor_segments + next_j
            v2 = next_i * minor_segments + next_j
            v3 = next_i * minor_segments + j
            
            torus_indices.extend([v0, v1, v2, v3])
            torus_counts.append(4)
    
    torus.GetPointsAttr().Set(torus_points)
    torus.GetFaceVertexIndicesAttr().Set(torus_indices)
    torus.GetFaceVertexCountsAttr().Set(torus_counts)
    torus.AddTranslateOp().Set(Gf.Vec3d(3, 1, 0))
    torus.GetDisplayColorAttr().Set([Gf.Vec3f(0.3, 0.6, 0.9)])
    
    # 바닥
    ground = UsdGeom.Mesh.Define(stage, '/World/Ground')
    ground.GetPointsAttr().Set([
        Gf.Vec3f(-8, 0, -8),
        Gf.Vec3f(8, 0, -8),
        Gf.Vec3f(8, 0, 8),
        Gf.Vec3f(-8, 0, 8)
    ])
    ground.GetFaceVertexIndicesAttr().Set([0, 1, 2, 3])
    ground.GetFaceVertexCountsAttr().Set([4])
    ground.GetDisplayColorAttr().Set([Gf.Vec3f(0.35, 0.35, 0.4)])
    
    # 조명
    light = UsdLux.DomeLight.Define(stage, '/World/DomeLight')
    light.GetIntensityAttr().Set(0.5)
    
    sun = UsdLux.DistantLight.Define(stage, '/World/Sun')
    sun.GetIntensityAttr().Set(1.0)
    sun.AddRotateXYZOp().Set(Gf.Vec3f(-50, 25, 0))
    
    stage.GetRootLayer().Save()
    print(f"생성됨: {filepath}")
    return filepath


def create_hierarchy_scene(filepath="hierarchy_scene.usda"):
    """계층 구조가 있는 씬"""
    stage = Usd.Stage.CreateNew(filepath)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    
    # 로봇 팔 계층 구조
    robot = UsdGeom.Xform.Define(stage, '/World/Robot')
    
    # 베이스
    base = UsdGeom.Cylinder.Define(stage, '/World/Robot/Base')
    base.GetRadiusAttr().Set(1.0)
    base.GetHeightAttr().Set(0.5)
    base.GetDisplayColorAttr().Set([Gf.Vec3f(0.3, 0.3, 0.35)])
    
    # 하단 암
    lower_arm = UsdGeom.Xform.Define(stage, '/World/Robot/Base/LowerArm')
    lower_arm.AddTranslateOp().Set(Gf.Vec3d(0, 0.5, 0))
    lower_arm.AddRotateXYZOp().Set(Gf.Vec3f(0, 0, 20))
    
    lower_arm_geom = UsdGeom.Capsule.Define(stage, '/World/Robot/Base/LowerArm/Geom')
    lower_arm_geom.GetRadiusAttr().Set(0.2)
    lower_arm_geom.GetHeightAttr().Set(2.0)
    lower_arm_geom.AddTranslateOp().Set(Gf.Vec3d(0, 1.2, 0))
    lower_arm_geom.GetDisplayColorAttr().Set([Gf.Vec3f(0.8, 0.4, 0.1)])
    
    # 상단 암
    upper_arm = UsdGeom.Xform.Define(stage, '/World/Robot/Base/LowerArm/UpperArm')
    upper_arm.AddTranslateOp().Set(Gf.Vec3d(0, 2.5, 0))
    upper_arm.AddRotateXYZOp().Set(Gf.Vec3f(0, 0, -40))
    
    upper_arm_geom = UsdGeom.Capsule.Define(stage, '/World/Robot/Base/LowerArm/UpperArm/Geom')
    upper_arm_geom.GetRadiusAttr().Set(0.15)
    upper_arm_geom.GetHeightAttr().Set(1.5)
    upper_arm_geom.AddTranslateOp().Set(Gf.Vec3d(0, 0.9, 0))
    upper_arm_geom.GetDisplayColorAttr().Set([Gf.Vec3f(0.8, 0.5, 0.1)])
    
    # 그리퍼
    gripper = UsdGeom.Xform.Define(stage, '/World/Robot/Base/LowerArm/UpperArm/Gripper')
    gripper.AddTranslateOp().Set(Gf.Vec3d(0, 1.8, 0))
    
    left_finger = UsdGeom.Cube.Define(stage, '/World/Robot/Base/LowerArm/UpperArm/Gripper/LeftFinger')
    left_finger.GetSizeAttr().Set(0.1)
    left_finger.AddScaleOp().Set(Gf.Vec3f(1, 3, 0.5))
    left_finger.AddTranslateOp().Set(Gf.Vec3d(-0.15, 0.15, 0))
    left_finger.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.2, 0.25)])
    
    right_finger = UsdGeom.Cube.Define(stage, '/World/Robot/Base/LowerArm/UpperArm/Gripper/RightFinger')
    right_finger.GetSizeAttr().Set(0.1)
    right_finger.AddScaleOp().Set(Gf.Vec3f(1, 3, 0.5))
    right_finger.AddTranslateOp().Set(Gf.Vec3d(0.15, 0.15, 0))
    right_finger.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.2, 0.25)])
    
    # 타겟 오브젝트
    target = UsdGeom.Sphere.Define(stage, '/World/Target')
    target.GetRadiusAttr().Set(0.3)
    target.AddTranslateOp().Set(Gf.Vec3d(2, 0.3, 0))
    target.GetDisplayColorAttr().Set([Gf.Vec3f(0.9, 0.2, 0.2)])
    
    # 바닥
    ground = UsdGeom.Mesh.Define(stage, '/World/Ground')
    ground.GetPointsAttr().Set([
        Gf.Vec3f(-5, 0, -5),
        Gf.Vec3f(5, 0, -5),
        Gf.Vec3f(5, 0, 5),
        Gf.Vec3f(-5, 0, 5)
    ])
    ground.GetFaceVertexIndicesAttr().Set([0, 1, 2, 3])
    ground.GetFaceVertexCountsAttr().Set([4])
    ground.GetDisplayColorAttr().Set([Gf.Vec3f(0.4, 0.4, 0.45)])
    
    # 조명
    light = UsdLux.DistantLight.Define(stage, '/World/Light')
    light.GetIntensityAttr().Set(1.2)
    light.AddRotateXYZOp().Set(Gf.Vec3f(-45, 30, 0))
    
    stage.GetRootLayer().Save()
    print(f"생성됨: {filepath}")
    return filepath


def create_animated_scene(filepath="animated_scene.usda"):
    """애니메이션이 있는 씬 (시간 샘플)"""
    stage = Usd.Stage.CreateNew(filepath)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    
    # 타임라인 설정
    stage.SetStartTimeCode(1)
    stage.SetEndTimeCode(120)
    stage.SetTimeCodesPerSecond(24)
    
    # 회전하는 큐브
    cube = UsdGeom.Cube.Define(stage, '/World/RotatingCube')
    cube.GetSizeAttr().Set(1.5)
    
    rotate_op = cube.AddRotateYOp()
    for frame in range(1, 121):
        rotate_op.Set(frame * 3.0, Usd.TimeCode(frame))
    
    cube.AddTranslateOp().Set(Gf.Vec3d(-3, 1, 0))
    cube.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.5, 0.9)])
    
    # 바운싱 구
    sphere = UsdGeom.Sphere.Define(stage, '/World/BouncingSphere')
    sphere.GetRadiusAttr().Set(0.8)
    
    translate_op = sphere.AddTranslateOp()
    for frame in range(1, 121):
        t = frame / 24.0
        y = abs(math.sin(t * 3)) * 2 + 0.8
        translate_op.Set(Gf.Vec3d(0, y, 0), Usd.TimeCode(frame))
    
    sphere.GetDisplayColorAttr().Set([Gf.Vec3f(0.9, 0.3, 0.2)])
    
    # 스케일 변화 실린더
    cylinder = UsdGeom.Cylinder.Define(stage, '/World/ScalingCylinder')
    cylinder.GetRadiusAttr().Set(0.5)
    cylinder.GetHeightAttr().Set(2.0)
    cylinder.AddTranslateOp().Set(Gf.Vec3d(3, 1, 0))
    
    scale_op = cylinder.AddScaleOp()
    for frame in range(1, 121):
        t = frame / 24.0
        s = 0.5 + 0.5 * math.sin(t * 2)
        scale_op.Set(Gf.Vec3f(1 + s * 0.5, 1, 1 + s * 0.5), Usd.TimeCode(frame))
    
    cylinder.GetDisplayColorAttr().Set([Gf.Vec3f(0.2, 0.8, 0.3)])
    
    # 바닥
    ground = UsdGeom.Mesh.Define(stage, '/World/Ground')
    ground.GetPointsAttr().Set([
        Gf.Vec3f(-8, 0, -8),
        Gf.Vec3f(8, 0, -8),
        Gf.Vec3f(8, 0, 8),
        Gf.Vec3f(-8, 0, 8)
    ])
    ground.GetFaceVertexIndicesAttr().Set([0, 1, 2, 3])
    ground.GetFaceVertexCountsAttr().Set([4])
    ground.GetDisplayColorAttr().Set([Gf.Vec3f(0.4, 0.4, 0.45)])
    
    # 조명
    light = UsdLux.DistantLight.Define(stage, '/World/Light')
    light.GetIntensityAttr().Set(1.2)
    light.AddRotateXYZOp().Set(Gf.Vec3f(-45, 30, 0))
    
    stage.GetRootLayer().Save()
    print(f"생성됨: {filepath}")
    print("  - 프레임 범위: 1-120 (5초 @ 24fps)")
    return filepath


def main():
    """모든 샘플 파일 생성"""
    print("=== USD 샘플 파일 생성 ===\n")
    
    files = [
        create_simple_scene("simple_scene.usda"),
        create_mesh_scene("mesh_scene.usda"),
        create_hierarchy_scene("hierarchy_scene.usda"),
        create_animated_scene("animated_scene.usda"),
    ]
    
    print("\n=== 생성 완료 ===")
    print("뷰어에서 테스트:")
    print("  python usd_basic_viewer.py simple_scene.usda")
    print("  python usd_hydra_viewer.py hierarchy_scene.usda")
    
    return files


if __name__ == "__main__":
    main()
