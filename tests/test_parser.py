from pathlib import Path

import pytest

from bbfmodels.ir import Access, ActiveNotify, BaseType, Document, Status
from bbfmodels.parser import ParseError, ParseWarning, parse, parse_file, sanitize

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def cwmp() -> Document:
    return parse_file(FIXTURES / "mini-cwmp-full.xml")


@pytest.fixture(scope="module")
def usp() -> Document:
    return parse_file(FIXTURES / "mini-usp-full.xml")


def test_sanitize_repairs_the_known_faults() -> None:
    assert sanitize("a & b") == "a &amp; b"
    assert sanitize("&amp; &#10; &#x1F;") == "&amp; &#10; &#x1F;"
    assert sanitize("the <OUI> part <string/>") == "the &lt;OUI> part <string/>"
    assert (
        sanitize('<default value=""" type="object"/>') == '<default value="&quot;" type="object"/>'
    )
    assert sanitize("<!-- c --> <?pi?> </object>") == "<!-- c --> <?pi?> </object>"


def test_document_header(cwmp: Document) -> None:
    assert cwmp.spec == "urn:example-org:mini-1-0-0-cwmp"
    assert cwmp.file == "mini-1-0-0-cwmp-full.xml"
    assert cwmp.protocol == "cwmp"
    assert "TR-181 & friends" in cwmp.description
    assert "<OUI>" in cwmp.description


def test_description_keeps_lines_and_paragraphs(cwmp: Document) -> None:
    radio = cwmp.models[0].objects["Device.Radio.{i}."]
    assert radio.description == "One radio.\n\nSecond paragraph with {{param|Enable}} markup."


def test_named_data_types_resolve_through_their_base(cwmp: Document) -> None:
    v4 = cwmp.data_types["IPv4Address"]
    assert v4.base == "IPAddress"
    assert v4.base_type is BaseType.STRING
    assert [s.max_length for s in v4.facets.sizes] == [15]
    assert [p.value for p in v4.facets.patterns] == ["", "[0-9.]+"]
    names = cwmp.data_types["Names"]
    assert names.list is not None and names.list.max_items == 4
    assert names.list.sizes[0].max_length == 256
    assert names.facets.sizes[0].max_length == 32


def test_objects_and_tables(cwmp: Document) -> None:
    model = cwmp.models[0]
    assert model.root == "Device" and model.version == "2.0"
    assert list(model.objects) == ["Device.", "Device.Radio.{i}.", "Device.Config.{i}."]
    root = model.objects["Device."]
    assert not root.multi_instance and root.parent_path == "" and root.name == "Device"
    radio = model.objects["Device.Radio.{i}."]
    assert radio.multi_instance and radio.name == "Radio" and radio.parent_path == "Device."
    assert radio.access is Access.READ_WRITE
    assert radio.min_entries == 0 and radio.max_entries is None
    assert radio.num_entries_parameter == "RadioNumberOfEntries"
    assert radio.enable_parameter == "Enable"
    assert [(k.functional, k.parameters) for k in radio.unique_keys] == [
        (False, ("Alias",)),
        (True, ("Name", "Channel")),
    ]


def test_parameter_attributes(cwmp: Document) -> None:
    root = cwmp.models[0].objects["Device."]
    password = root.parameters["Password"]
    assert password.active_notify is ActiveNotify.CAN_DENY
    assert password.syntax.hidden
    assert password.syntax.default is not None
    assert password.syntax.default.kind == "factory" and password.syntax.default.value == '"'
    reset = root.parameters["Reset"]
    assert reset.status is Status.DEPRECATED
    assert reset.syntax.command and reset.syntax.base_type is BaseType.BOOLEAN


def test_syntax_facets(cwmp: Document) -> None:
    p = cwmp.models[0].objects["Device.Radio.{i}."].parameters
    channel = p["Channel"].syntax
    assert channel.base_type is BaseType.UNSIGNED_INT
    assert channel.facets.ranges[0].min_inclusive == 1
    assert channel.facets.ranges[0].max_inclusive == 255
    assert channel.facets.units == "channel"
    band = p["Band"].syntax.facets.enumerations
    assert [e.value for e in band] == ["2.4GHz", "5GHz", "6GHz"]
    assert band[1].optional and not band[0].optional
    assert band[2].status is Status.DEPRECATED and band[2].code == 6
    assert band[2].description == "Six."
    standards = p["Standards"].syntax
    assert standards.list is not None and standards.list.max_items == 3
    assert len(standards.facets.enumerations) == 2
    assert p["LowerLayer"].syntax.facets.path_ref is not None
    assert p["LowerLayer"].syntax.facets.path_ref.ref_type == "weak"
    assert p["LowerLayer"].syntax.facets.path_ref.target_parent == "Device.Radio."
    assert p["Mode"].syntax.facets.enumeration_ref is not None
    assert p["Mode"].syntax.facets.enumeration_ref.target_param == "#.ModesSupported"
    assert p["Mode"].syntax.facets.enumeration_ref.null_value == ""


def test_named_type_in_syntax_is_resolved_and_narrowed(cwmp: Document) -> None:
    p = cwmp.models[0].objects["Device.Radio.{i}."].parameters
    sent = p["BytesSent"].syntax
    assert sent.data_type == "StatsCounter32"
    assert sent.base_type is BaseType.UNSIGNED_INT
    assert sent.facets.units == "bytes"
    address = p["Address"].syntax
    assert address.data_type == "IPv4Address"
    assert address.facets.sizes[0].max_length == 15
    assert [x.value for x in address.facets.patterns] == ["", "[0-9.]+"]
    aliases = p["Aliases"].syntax
    assert aliases.list is not None and aliases.list.max_items == 4


def test_profiles(cwmp: Document) -> None:
    profiles = cwmp.models[0].profiles
    baseline = profiles["Baseline:1"]
    assert baseline.objects["Device.Radio.{i}."].requirement == "createDelete"
    assert baseline.objects["Device.Radio.{i}."].parameters == {"Enable": "readWrite"}
    radio = profiles["Radio:2"]
    assert radio.base == "Baseline:1"
    assert radio.extends == ("Other:1", "Another:1")
    assert radio.status is Status.DEPRECATED


def test_usp_commands_and_events(usp: Document) -> None:
    assert usp.protocol == "usp"
    root = usp.models[0].objects["Device."]
    reboot = root.commands["Reboot()"]
    assert not reboot.is_async and reboot.description == "Reboot."
    assert reboot.input.parameters["Cause"].mandatory is False
    assert reboot.input.parameters["Cause"].access is None
    trace = root.commands["TraceRoute()"]
    assert trace.is_async
    assert trace.input.parameters["Host"].mandatory is True
    assert trace.output.parameters["ResponseTime"].syntax.facets.units == "milliseconds"
    hops = trace.output.objects["RouteHops.{i}."]
    assert hops.multi_instance and hops.max_entries is None
    assert list(hops.parameters) == ["Host"]
    boot = root.events["Boot!"]
    assert boot.version == "2.0" and list(boot.arguments.parameters) == ["CommandKey"]
    assert usp.models[0].objects["Device.Services."].mount_type == "mountPoint"


def test_ir_round_trips_through_json(cwmp: Document, usp: Document) -> None:
    for doc in (cwmp, usp):
        text = doc.model_dump_json(exclude_defaults=True)
        assert Document.model_validate_json(text) == doc


def test_rejects_what_is_not_a_model() -> None:
    with pytest.raises(ParseError, match="not a data model document"):
        parse("<unclosed>")
    with pytest.raises(ParseError, match="expected <document>"):
        parse("<model/>")
    with pytest.raises(ParseError, match=r"-full\.xml"):
        parse('<dm:document xmlns:dm="x" spec="s"><import file="a"/></dm:document>')
    with pytest.raises(ParseError, match="not defined"):
        parse(
            '<dm:document xmlns:dm="x" spec="s"><model name="D:1"><object name="D." '
            'minEntries="1" maxEntries="1"><parameter name="P" access="readOnly">'
            '<syntax><dataType ref="Nope"/></syntax></parameter></object></model></dm:document>'
        )


def test_a_typeless_syntax_is_a_string_with_a_warning() -> None:
    text = (
        '<dm:document xmlns:dm="x" spec="s"><model name="D:1"><object name="D." '
        'minEntries="1" maxEntries="1"><parameter name="P" access="readOnly">'
        "<syntax/></parameter></object></model></dm:document>"
    )
    with pytest.warns(ParseWarning, match="D.P has a syntax without a type"):
        doc = parse(text)
    assert doc.models[0].objects["D."].parameters["P"].syntax.base_type is BaseType.STRING


def test_unknown_vocabulary_values_fall_back_with_a_warning() -> None:
    text = (
        '<dm:document xmlns:dm="x" spec="s"><model name="D:1"><object name="D." '
        'access="readOnly" minEntries="1" maxEntries="1" status="odd">'
        '<parameter name="P" access="writeSometimes" activeNotify="forceDefaultPolled">'
        "<syntax><string/></syntax></parameter></object></model></dm:document>"
    )
    with pytest.warns(ParseWarning) as record:
        doc = parse(text)
    messages = sorted(str(w.message) for w in record)
    assert messages == [
        "D.: 'odd' is not a Status; read as 'current'",
        "D.P: 'forceDefaultPolled' is not a ActiveNotify; read as 'normal'",
        "D.P: 'writeSometimes' is not a Access; read as 'readOnly'",
    ]
    param = doc.models[0].objects["D."].parameters["P"]
    assert param.access is Access.READ_ONLY
    assert param.active_notify is ActiveNotify.NORMAL
    assert doc.models[0].objects["D."].status is Status.CURRENT


def test_other_document_faults_are_parse_errors() -> None:
    text = (
        '<dm:document xmlns:dm="x" spec="s"><model name="D:1"><object name="D." '
        'minEntries="1" maxEntries="1"><parameter name="P" access="readOnly">'
        '<syntax><unsignedInt><range minInclusive="low"/></unsignedInt></syntax>'
        "</parameter></object></model></dm:document>"
    )
    with pytest.raises(ParseError, match="not an integer"):
        parse(text)
