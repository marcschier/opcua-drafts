"""The machine-readable contract of OPC 20020 — UA Companion Specification Template.

Every rule here was derived by unpacking the template; the reasoning is recorded in
skills/opcua-spec-to-word/reference/template-contract.md. The validator enforces this
contract against the *produced* document, independently of the writer.
"""

TEMPLATE_VERSION = '1.01.19'

# --------------------------------------------------------------------------- styles

# Paragraph styles the writer is allowed to emit. Anything else is a defect: the
# template defines 180 styles but only these carry the house formatting the OPC
# Foundation editors expect.
ALLOWED_PARAGRAPH_STYLES = {
    # structure
    'Heading1', 'Heading2', 'Heading3', 'Heading4', 'Heading5',
    'ANNEXtitle', 'ANNEX-heading1', 'ANNEX-heading2', 'ANNEX-heading3',
    'HEADINGNonumber', 'MAIN-TITLE', 'DocumentTitle', 'Title',
    # body text
    'PARAGRAPH', 'PARAGRAPHCompressed', 'PARAGRAPHKWNP', 'Normal', 'NormalWeb',
    'NoSpacing', 'spacer', 'Spacer0', 'FOREWORD', 'ForwordIntroduction',
    'StyleSectionHeadingArial',
    # lists
    'ListBullet', 'ListBullet2', 'ListBullet3', 'ListDash', 'ListDash2',
    'ListNumber', 'ListNumber2', 'ListParagraph',
    # captions and floats
    'TABLE-title', 'FIGURE', 'FIGURE-title', 'FIGURE-uncaptioned', 'Figure0', 'Caption',
    # tables
    'TableText', 'TableTextWithTabs', 'TableHead', 'TableNotes',
    'TABLE-cell', 'TABLE-centered', 'TABLE-col-heading',
    # notes, examples, code
    'NOTE', 'EXAMPLE', 'CODE', 'CODE-TableCell', 'MethodSignature',
    # terms
    'TERM', 'TERM-number', 'TERM-number3', 'TERM-number4', 'TERM-definition',
    'TERM-note', 'TERM-example', 'TERM-source', 'TERM-admitted',
    # references
    'ReferenceDocuments', 'BIBLIOGRAPHY-numbered',
    # generated tables of contents
    'TOC1', 'TOC2', 'TOC3', 'TOCHeading', 'TableofFigures',
}

ALLOWED_CHARACTER_STYLES = {
    'Reference', 'VARIABLE', 'Strong', 'Emphasis', 'Hyperlink', 'FollowedHyperlink',
    'SUBscript', 'SUPerscript', 'SMALLCAPS', 'TableTextChar', 'PARAGRAPHChar',
}

# Styles that carry an automatic clause number from word/numbering.xml. Heading text
# in these styles must never contain a literal number — Word supplies it.
AUTO_NUMBERED_STYLES = {
    'Heading1', 'Heading2', 'Heading3', 'Heading4', 'Heading5',
    'ANNEXtitle', 'ANNEX-heading1', 'ANNEX-heading2', 'ANNEX-heading3',
}

# numId values used by the template for the two heading sequences and for body lists.
NUMID_HEADINGS = 23
NUMID_ANNEXES = 14
NUMID_SCOPE_BULLETS = 19
NUMID_BULLETS = 21

# --------------------------------------------------------------------------- tables

# Column grid of the normative type-definition table (Table 2 of the template),
# in twentieths of a point. Total 8926 dxa == the template's text width.
TYPE_TABLE_GRID = [1696, 1134, 2127, 1275, 1843, 851]

# Header row of the References block inside a type-definition table.
TYPE_TABLE_REFERENCE_HEADERS = [
    'References', 'NodeClass', 'BrowseName', 'DataType', 'TypeDefinition', 'Other',
]

# Additional-references table (Table 4).
ADDITIONAL_REFERENCES_GRID = [2400, 2100, 1200, 3226]
ADDITIONAL_REFERENCES_HEADERS = [
    'SourceBrowsePath', 'Reference Type', 'Is Forward', 'TargetBrowsePath',
]

# Additional sub-components table (Table 5).
ADDITIONAL_SUBCOMPONENTS_GRID = [1500, 1400, 900, 1700, 1200, 1500, 726]
ADDITIONAL_SUBCOMPONENTS_HEADERS = [
    'BrowsePath', 'References', 'NodeClass', 'BrowseName', 'DataType',
    'TypeDefinition', 'Others',
]

# Attribute-values table (Table 6).
ATTRIBUTE_VALUES_GRID = [2400, 2600, 3926]

# Structure / enumeration tables (Tables 12-14, 31, 33).
STRUCTURE_GRID = [2200, 1900, 4826]
STRUCTURE_HEADERS = ['Name', 'Type', 'Description']
ENUM_GRID = [2200, 1200, 5526]
ENUM_HEADERS = ['Name', 'Value', 'Description']

# Namespace tables (Tables 39, 40).
NAMESPACE_SERVER_GRID = [3400, 5526]
NAMESPACE_DOC_GRID = [3800, 1600, 3526]

# Two-column generic table used for method arguments, mapping tables and the like.
GENERIC_TABLE_TOTAL = 8926

# --------------------------------------------------------------------------- modelling rules

# Short names permitted in the "Other" column (Table 3 of the template).
MODELLING_RULE_SHORT = {
    'Mandatory': 'M',
    'Optional': 'O',
    'MandatoryPlaceholder': 'MP',
    'OptionalPlaceholder': 'OP',
}
OTHER_SHORT = dict(MODELLING_RULE_SHORT)
OTHER_SHORT.update({'ReadOnly': 'RO', 'ReadWrite': 'RW', 'WriteOnly': 'WO'})

# Guideline 3: HasSubtype references are removed from type-definition tables because
# they conflict with the ConformanceUnit references.
SUPPRESSED_REFERENCE_TYPES = {'HasSubtype'}

# --------------------------------------------------------------------------- policy

# Guideline 5: search or permanent links into the online reference must not appear.
FORBIDDEN_LINK_HOSTS = ('reference.opcfoundation.org',)

# Tokens the template ships that must not survive into a finished document unless the
# build config deliberately keeps them (the draft keeps the identity placeholders).
PLACEHOLDER_TOKENS = (
    '<title>', '<Title>', '<short name>', '<other organization>', '<some>',
    '<someStructure>', '<someUnion>', '<someEnumeration>', '<someOptionSet>',
    '<someReferenceType>', '<someInstance>', '<Type>', '<TheLocationInAddressSpace>',
    'XXXXX', '<mm>',
)

# Identity placeholders this draft intentionally retains, per the build decision to keep
# the template's own placeholders until the OPC Foundation assigns real values.
RETAINED_PLACEHOLDER_TOKENS = ('OPC nnnnn-m', 'project_id=<nnn>', '<nnn>')

# --------------------------------------------------------------------------- properties

# Custom document properties surfaced through DOCPROPERTY fields in the cover and headers.
DOC_PROPERTY_KEYS = (
    'Version', 'Published', 'OPCVersion', 'OPCReleaseType', 'Part Name', 'Part Number',
    'HeaderLeft', 'DocNumber', 'HeaderRight', 'TemplateVersion', 'Date completed',
)

# --------------------------------------------------------------------------- clause plan

# The clause skeleton the template mandates, in order. `optional` clauses are dropped
# when the model has no content for them; clause 4 of the template (EDITING Guidelines)
# is always removed because the template says to delete it before publication.
CLAUSE_SKELETON = (
    ('scope', 'Scope', False),
    ('normative-references', 'Normative references', False),
    ('terms', 'Terms, abbreviated terms and conventions', False),
    ('general', 'General information to {title} and OPC UA', False),
    ('use-cases', 'Use cases', False),
    ('model-overview', '{title} information model overview', False),
    ('objecttypes', 'OPC UA ObjectTypes', True),
    ('eventtypes', 'OPC UA EventTypes', True),
    ('variabletypes', 'OPC UA VariableTypes', True),
    ('datatypes', 'OPC UA DataTypes', True),
    ('referencetypes', 'OPC UA ReferenceTypes', True),
    ('instances', 'Instances', True),
    ('well-known-browsenames', 'Well-Known BrowseNames', True),
    ('profiles', 'Profiles and conformance units', False),
    ('namespaces', 'Namespaces', False),
)


def modelling_rule_short(name):
    """Map a ModellingRule BrowseName to the short form used in the Other column."""
    return MODELLING_RULE_SHORT.get(name, name)
