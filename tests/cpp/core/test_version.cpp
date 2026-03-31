#include <cstdio>
#include <string>

#include "doctest/doctest.h"
#include "rogue/GeneralError.h"
#include "rogue/Version.h"

namespace {

std::string normalizedCurrentVersion() {
    const std::string current = rogue::Version::current();
    uint32_t major            = 0;
    uint32_t minor            = 0;
    uint32_t maint            = 0;
    const int parsed          = std::sscanf(current.c_str(), "v%u.%u.%u", &major, &minor, &maint);

    REQUIRE_EQ(parsed, 3);

    return std::to_string(major) + "." + std::to_string(minor) + "." + std::to_string(maint);
}

}  // namespace

TEST_CASE("Version helpers stay internally consistent") {
    const std::string current    = rogue::Version::current();
    const std::string normalized = normalizedCurrentVersion();

    REQUIRE_FALSE(current.empty());
    CHECK(current[0] == 'v' || current[0] == 'V');

    CHECK_EQ(rogue::Version::getMajor() + 0U, rogue::Version::getMajor());
    CHECK_EQ(rogue::Version::getMinor() + 0U, rogue::Version::getMinor());
    CHECK_EQ(rogue::Version::getMaint() + 0U, rogue::Version::getMaint());

    CHECK(rogue::Version::greaterThanEqual(normalized));
    CHECK(rogue::Version::lessThanEqual(normalized));
    CHECK_FALSE(rogue::Version::greaterThan(normalized));
    CHECK_FALSE(rogue::Version::lessThan(normalized));

    CHECK_EQ(rogue::Version::pythonVersion().find(normalized), static_cast<std::string::size_type>(0));
}

TEST_CASE("Version comparison and validation helpers reject malformed versions") {
    CHECK_THROWS_AS(rogue::Version::greaterThanEqual("bad.version"), rogue::GeneralError);
    CHECK_THROWS_AS(rogue::Version::greaterThan("bad.version"), rogue::GeneralError);
    CHECK_THROWS_AS(rogue::Version::lessThanEqual("bad.version"), rogue::GeneralError);
    CHECK_THROWS_AS(rogue::Version::lessThan("bad.version"), rogue::GeneralError);
    CHECK_THROWS_AS(rogue::Version::minVersion("bad.version"), rogue::GeneralError);
    CHECK_THROWS_AS(rogue::Version::maxVersion("bad.version"), rogue::GeneralError);
    CHECK_THROWS_AS(rogue::Version::exactVersion("bad.version"), rogue::GeneralError);
}

TEST_CASE("Version threshold helpers accept the compiled version tuple") {
    const std::string normalized = normalizedCurrentVersion();

    CHECK(rogue::Version::greaterThanEqual("0.0.0"));
    CHECK_FALSE(rogue::Version::lessThan("0.0.0"));

    rogue::Version::minVersion(normalized);
    rogue::Version::maxVersion(normalized);
    rogue::Version::exactVersion(normalized);
}
