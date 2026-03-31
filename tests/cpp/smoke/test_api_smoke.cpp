#include "rogue/Directives.h"

#include <string>

#define NO_IMPORT_ARRAY
#include "doctest/doctest.h"
#include "rogue/interfaces/api/Bsp.h"
#include "rogue/numpy.h"
#include "support/test_python.h"

TEST_CASE("C++ API smoke test exercises the example root") {
    try {
        REQUIRE_EQ(rogue_test_initialize_python_numpy(), 0);

        namespace bp = boost::python;
        bp::object main      = bp::import("__main__");
        bp::object globals   = main.attr("__dict__");
        const char* bootstrap = R"PY(
import sys
import types
import pyrogue as pr

module = types.ModuleType("rogue_cpp_api_smoke")

class AxiVersion(pr.Device):
    def __init__(self, **kwargs):
        super().__init__(name="AxiVersion", **kwargs)
        self.add(pr.LocalVariable(name="ScratchPad", mode="RW", value="0x00000000"))

class TestRoot(pr.Root):
    def __init__(self):
        super().__init__(name="ExampleRoot", description="C++ API smoke root", pollEn=False)
        self.add(AxiVersion())

module.TestRoot = TestRoot
sys.modules["rogue_cpp_api_smoke"] = module
)PY";

        bp::exec(bootstrap, globals, globals);

        rogue::interfaces::api::Bsp bsp("rogue_cpp_api_smoke", "TestRoot");

        CHECK_EQ(bsp.getAttribute("name"), std::string("ExampleRoot"));

        auto scratchPad = bsp["AxiVersion"]["ScratchPad"];
        scratchPad.setWrite("0x1111");

        const std::string cachedValue = scratchPad.get();
        const std::string readValue   = scratchPad.readGet();

        CHECK_NE(cachedValue.find("1111"), std::string::npos);
        CHECK_EQ(readValue, cachedValue);
        CHECK_NE(bsp.getNode("ExampleRoot.AxiVersion.ScratchPad")->get().find("1111"), std::string::npos);

        const std::string yamlConfig = bsp["GetYamlConfig"]("True");
        CHECK_NE(yamlConfig.find("AxiVersion"), std::string::npos);

        bsp["WriteAll"]();
        bsp["ReadAll"]();
    } catch (...) {
        if (PyErr_Occurred()) {
            PyErr_Print();
            PyErr_Clear();
        }
        REQUIRE(false);
    }
}
