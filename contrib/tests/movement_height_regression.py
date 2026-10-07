"""Focused native regression checks for the movement-height crash.

Run from an MSVC developer shell:
    python contrib/tests/movement_height_regression.py --compiler cl
The harness compiles the actual changed C++ bodies with controlled interfaces.
It does not start a realm or require a database or extracted client data.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path


def block(text, marker):
    start = text.index(marker)
    opening = text.index("{", start)
    depth = 0
    for index in range(opening, len(text)):
        depth += (text[index] == "{") - (text[index] == "}")
        if depth == 0:
            return text[start:index + 1]
    raise AssertionError(f"Unclosed block: {marker}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", default="cl")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    script = (root / "src/game/DBScripts/ScriptMgr.cpp").read_text()
    dynamic = script[script.index("case SCRIPT_COMMAND_MOVE_DYNAMIC:", script.index("ScriptAction::ExecuteDbscriptCommand")):]
    movement = block(dynamic, "if (m_script->data_flags & SCRIPT_FLAG_COMMAND_ADDITIONAL)")
    tree_path = root / "src/game/Vmap/MapTree.cpp"
    if not tree_path.exists():
        tree_path = root / "src/game/vmap/MapTree.cpp"
    tree = tree_path.read_text()
    height = block(tree, "float StaticMapTree::getHeight(")
    terrain = (root / "src/game/Maps/GridMap.cpp").read_text()
    terrain = block(terrain, "float TerrainInfo::GetHeightStatic(")
    terrain_guard = terrain[terrain.index("{") + 1:terrain.index("float mapHeight")]
    destination_guard = block(dynamic, "if (!MaNGOS::IsValidMapCoord(x, y, z))")
    map_source = (root / "src/game/Maps/Map.cpp").read_text()
    map_height = block(map_source, "float Map::GetHeight(")
    map_guard = map_height[map_height.index("{") + 1:map_height.index("float staticHeight")]

    # Deterministically seed the same invalid height observed in the crash.
    # Only the real movement branch can replace it before the mock height query.
    harness = r"""
#include <cassert>
#include <cmath>
#include <limits>
#include <iostream>
struct Vector3 {
    float x=0, y=0, z=0;
    Vector3() = default;
    Vector3(float a, float b, float c): x(a), y(b), z(c) {}
    bool isFinite() const { return std::isfinite(x) && std::isfinite(y) && std::isfinite(z); }
};
namespace G3D {
float inf() { return std::numeric_limits<float>::infinity(); }
struct Ray { Vector3 origin, dir; Ray(Vector3 a, Vector3 b): origin(a), dir(b) {} };
}
struct StaticMapTree {
    mutable int calls=0;
    mutable float direction=0;
    bool hit=true;
    bool getIntersectionTime(const G3D::Ray& ray, float& distance) const {
        ++calls; direction=ray.dir.z; distance=5.f; return hit;
    }
    float getHeight(const Vector3&, float) const;
};
__HEIGHT__
namespace MaNGOS {
bool IsValidMapCoord(float x, float y, float z) {
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z)
        && std::abs(x) < 17067.f && std::abs(y) < 17067.f;
}
}
constexpr float VMAP_INVALID_HEIGHT_VALUE = -200000.f;
constexpr float INVALID_HEIGHT = VMAP_INVALID_HEIGHT_VALUE;
float mapEntry(float x, float y, float z) {
__MAP__
    return 456.f; // Valid queries can reach static and dynamic collision.
}
float terrainEntry(float x, float y, float z, float maxSearchDist) {
__TERRAIN__
    return 123.f; // Valid queries continue into the existing terrain implementation.
}
struct Logger { template<class... T> void outErrorDb(T...) {} } sLog;
struct Script {
    unsigned int data_flags=8, id=18020;
    struct { float fixedDist=3.f; } moveDynamic;
};
struct Object {
    float height, expected;
    int calls=0;
    float GetPositionX() const { return 3017.689941f; }
    float GetPositionY() const { return 3962.300049f; }
    float GetPositionZ() const { return height; }
    void* GetMap() { return this; }
    float GetAngle(Object*) const { return 0.f; }
    void GetNearPoint2dAt(float a, float b, float& x, float& y, float dist, float) {
        x=a+dist; y=b;
    }
    void UpdateAllowedPositionZ(float, float, float& z, void*) {
        ++calls;
        assert(std::isfinite(z) && z == expected);
        z += 0.5f; // Simulated ground adjustment must still run.
    }
};
bool move(float targetZ) {
    constexpr unsigned int SCRIPT_FLAG_COMMAND_ADDITIONAL=8;
    Script data; Script* m_script=&data;
    const char* m_table="dbscripts_on_relay";
    Object target{targetZ,targetZ}, actor{900.f,targetZ};
    Object* pTarget=&target; Object* source=&actor;
    float x=0.f, y=0.f, z=std::numeric_limits<float>::quiet_NaN();
__MOVEMENT__
__DESTINATION__
    assert(actor.calls == 1 && z == targetZ+0.5f);
    return true;
}
bool validDestination(float x, float y, float z) {
    Script data; Script* m_script=&data;
    const char* m_table="dbscripts_on_relay";
__DESTINATION__
    return true;
}
int main() {
    assert(move(156.184998f));
    assert(move(0.f));
    assert(move(-40.f));
    const float nan=std::numeric_limits<float>::quiet_NaN();
    const float inf=G3D::inf();
    StaticMapTree tree;
    for (float bad : {nan, inf, -inf}) {
        assert(tree.getHeight(Vector3(bad,2,10),50)==inf);
        assert(tree.getHeight(Vector3(1,bad,10),50)==inf);
        assert(tree.getHeight(Vector3(1,2,bad),50)==inf);
        assert(terrainEntry(bad,2,10,50)==VMAP_INVALID_HEIGHT_VALUE);
        assert(terrainEntry(1,bad,10,50)==VMAP_INVALID_HEIGHT_VALUE);
        assert(terrainEntry(1,2,bad,50)==VMAP_INVALID_HEIGHT_VALUE);
        assert(!validDestination(1,2,bad));
        assert(mapEntry(bad,2,10)==INVALID_HEIGHT);
        assert(mapEntry(1,bad,10)==INVALID_HEIGHT);
        assert(mapEntry(1,2,bad)==INVALID_HEIGHT);
    }
    assert(tree.getHeight(Vector3(1,2,10),nan)==inf);
    assert(tree.calls==0); // No invalid input may enter collision traversal.
    assert(terrainEntry(1,2,10,nan)==VMAP_INVALID_HEIGHT_VALUE);
    assert(terrainEntry(20000,2,10,50)==VMAP_INVALID_HEIGHT_VALUE);
    assert(terrainEntry(1,2,10,50)==123.f);
    assert(terrainEntry(1,2,10,-50)==123.f);
    assert(terrainEntry(1,2,10,inf)==123.f);
    assert(validDestination(3020.362305f,3963.663086f,156.184998f));
    assert(mapEntry(3020.362305f,3963.663086f,156.184998f)==456.f);
    assert(tree.getHeight(Vector3(1,2,10),50)==5.f && tree.direction==-1.f);
    assert(tree.getHeight(Vector3(1,2,10),-50)==15.f && tree.direction==1.f);
    assert(tree.getHeight(Vector3(1,2,10),inf)==5.f);
    assert(tree.getHeight(Vector3(1,2,10),-inf)==15.f);
    tree.hit=false;
    assert(tree.getHeight(Vector3(1,2,10),50)==inf);
    std::cout << "PASS: target height, invalid-input rejection, upward/downward and unbounded searches, no-hit behavior\n";
}
"""
    harness = (harness.replace("__HEIGHT__", height).replace("__TERRAIN__", terrain_guard)
        .replace("__MOVEMENT__", movement).replace("__DESTINATION__", destination_guard)
        .replace("__MAP__", map_guard))
    with tempfile.TemporaryDirectory(prefix="mantech-height-test-") as temp:
        temp = Path(temp)
        source = temp / "regression.cpp"
        source.write_text(harness)
        exe = temp / "regression.exe"
        subprocess.run([args.compiler, "/nologo", "/std:c++20", "/EHsc", "/Od",
            "/W4", "/WX", "/MD", str(source), "/Fe:" + str(exe),
            "/Fo:" + str(temp / "regression.obj")], cwd=temp, check=True)
        subprocess.run([str(exe)], cwd=temp, timeout=10, check=True)


if __name__ == "__main__":
    main()
