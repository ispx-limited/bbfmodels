from bbfmodels.describe import render
from bbfmodels.ir import BaseType, Enumeration, Facets, Pattern, Range, Syntax
from bbfmodels.parser import parse_file

SYNTAX = Syntax(
    base_type=BaseType.UNSIGNED_INT,
    data_type="Dbm1000",
    facets=Facets(
        units="seconds",
        enumerations=(Enumeration(value="Up"), Enumeration(value="Down")),
        ranges=(Range(min_inclusive=1, max_inclusive=255),),
        patterns=(Pattern(value="[0-9]+"),),
    ),
)


def test_templates_become_prose() -> None:
    assert (
        render("The time in {{units}} since {{param|Boot}}.", SYNTAX)
        == "The time in seconds since Boot."
    )
    assert (
        render("{{list}} {{reference|a ''Host'' row}}")
        == "Comma-separated list. A reference to a Host row."
    )
    assert render("{{list|each an Ethertype}}") == "Comma-separated list, each an Ethertype."
    assert (
        render("See {{bibref|TR-181i2|Section 4.2}} and {{bibref|RFC2863}}.")
        == "See [TR-181i2 Section 4.2] and [RFC2863]."
    )
    assert (
        render("Set to {{true}} or {{empty}}; {{null}} is {{false}}.")
        == "Set to true or an empty string; null is false."
    )
    assert render("{{numentries}}") == "The number of entries in the table."
    assert render("{{enum|Up|Status}} or {{enum|Down}}") == '"Up" or "Down"'
    assert render("State. {{enum}}", SYNTAX) == "State. Enumeration of: Up, Down."
    assert render("{{range}} {{pattern}}", SYNTAX) == "Range: 1 to 255. Pattern: [0-9]+."
    assert render("{{datatype}} and {{datatype|expand}}", SYNTAX) == "Dbm1000 and Dbm1000"
    assert (
        render("{{deprecated|2.11|because {{object|Device.X.}} went}}")
        == "Deprecated in 2.11: because Device.X went"
    )
    assert render("{{obsoleted|2.14}} {{deleted|2.18}}") == "Obsoleted in 2.14. Deleted in 2.18."
    assert render("{{template|Reset}} {{section|table}} {{nolist}} x") == "x"
    assert (
        render("{{command|#.Activate()}} {{event|Boot!}} {{command}}")
        == "#.Activate() Boot! this command"
    )
    assert (
        render("{{hidden}} {{maxval}} {{keys}}")
        == "The value is hidden when read. the maximum value"
    )
    assert render("{{unknownthing|a}}") == "{{unknownthing|a}}"


def test_bare_param_and_object_name_their_subject() -> None:
    text = "If {{param}} is {{true}}, {{object}} resets. See {{object|Device.WiFi.Radio.{i}.}}."
    assert render(text, parameter="Enable", object="Radio") == (
        "If Enable is true, Radio resets. See Device.WiFi.Radio.{i}."
    )
    assert render("{{param}} and {{object}}") == "this parameter and this object"


def test_datatype_expands_to_its_description() -> None:
    doc = parse_file("tests/fixtures/mini-cwmp-full.xml")
    alias = doc.models[0].objects["Device.Radio.{i}."].parameters["Alias"]
    assert render("{{datatype|expand}}", alias.syntax, doc.data_types) == "A non-volatile handle."
    assert render("{{datatype}}", alias.syntax, doc.data_types) == "Alias"


def test_paragraphs_and_spacing_survive() -> None:
    assert render("One radio.\n\nSecond paragraph with {{param|Enable}} markup.") == (
        "One radio.\n\nSecond paragraph with Enable markup."
    )
    assert render("a  ''b''   c .") == "a b c."
    assert render("One.\n\n{{template|Gone}}\n\nTwo.") == "One.\n\nTwo."
