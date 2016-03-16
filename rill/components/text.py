from rill.engine.component import *

"""
 * Affix each packet IN with the given Strings PRE before and POST after, and copy it to OUT.
 *
"""


@component
@outport("OUT")
@inport("IN")
@inport("PRE")
def Prefix(IN, PRE, OUT):
    """Prefix each packet IN with the given PRE and copy it to OUT"""
    prefix = PRE.receive_once("")

    for p in IN:
        text = prefix + p.get_content()
        p.drop()
        OUT.send(text)


@component
@outport("OUT", type=str)
@inport("IN", type=str)
@inport("PRE", type=str)
@inport("POST", type=str)
def Affix(IN, PRE, POST, OUT):
    """For each packet IN add the Strings PRE as a prefix and POST as a suffix,
    and copy to OUT"""
    spre = PRE.receive_once(default="")
    spost = POST.receive_once(default="")

    for pin in IN:
        sout = spre + pin.get_content() + spost
        pin.drop()
        OUT.send(sout)


def Affix2(IN, PRE, POST, OUT):
    spre = PRE.receive_once(default="")
    spost = POST.receive_once(default="")

    for pin in IN:
        sout = spre + pin.consume() + spost
        OUT.send(sout)


def Affix3(IN, PRE, POST, OUT):
    spre = PRE.receive_once(default="")
    spost = POST.receive_once(default="")

    for s in consume(IN):
        sout = spre + s + spost
        OUT.send(sout)


def Affix4(IN, PRE, POST, OUT):
    spre = PRE.receive_once(default="")
    spost = POST.receive_once(default="")

    for s in IN.iter_contents():
        sout = spre + s + spost
        OUT.send(sout)

@component
@outport("OUT", type=str)
@inport("IN", type=str)
def DedupeSuccessive(IN, OUT):
    """Take text IN and only send OUT where self differs from the previous
    text."""
    previous = ""
    for pin in IN:
        sin = pin.get_content()
        pin.drop()
        if not previous == sin:
            OUT.send(sin)
        previous = sin


@component
@inport("IN", type=str)
@outport("OUT", type=str)
@outport("DUPLICATE", type=str)
def DuplicateString(IN, OUT, DUPLICATE):
    """Copy all incoming packets to outputs OUT and DUPLICATE"""
    for p in IN:
        s = p.get_content()
        OUT.send(p)
        DUPLICATE.send(str(s))


"""Provide maximum field lengths from a stream of character-separated records
"""


# @component
# @ComponentDescription(
#     "Pass through a CSV stream, also output LIMITS of field lengths as CSV")
# @outport("OUT")
# @outport("LIMITS")
# @inport("IN")
# @inport("SEP")
# def FieldLimits(IN, OUT):
#     # Default separator
#     sep = ","
#
#     # Get separator from SEP IIP
#     psep = sepport.receive()
#     if (psep is not None):
#         sepport.close()
#         sep = psep.get_content()
#         self.drop(psep)
#
#     # Pass through IN to OUT, keeping greatest field lengths
#     int[]
#     nlimits = None
#     p
#     for p in IN:
#         o = p.get_content()
#
#         # Get fields for self record
#         fields = o.split(sep)
#
#         # Prepare limits data
#         if (nlimits is None):
#             nlimits = int[fields.length]
#         # Remember greatest field length
#         for (i = 0 i < nlimits.length i += 1):
#             if (fields[i].length() > nlimits[i]):
#                 nlimits[i] = fields[i].length()
#         # Pass through
#         outport.send(p)
#     if (nlimits is not None):
#         # Send LIMITS as single CSV record
#         slimits = ""
#         for (j = 0 j < nlimits.length j += 1):
#             slimits = slimits + nlimits[j]
#             if (j < nlimits.length - 1):
#                 slimits += sep
#         plimits = self.create(slimits)
#         # limitport.send(plimits)


@component
@outport("OUT", type=str)
@inport("IN", type=str)
def LineToWords(IN, OUT):
    """Take space-separated words in a record IN and deliver individual words
    OUT"""
    for pin in IN:
        w = pin.get_content()
        pin.drop()
        words = w.split(" ")
        for word in words:
            OUT.send(word)


@component
@outport("OUT", type=str)
@inport("IN", type=str)
def LowerCase(IN, OUT):
    """Convert text IN to lower case and send OUT"""
    for pin in IN:
        sin = pin.get_content()
        pin.drop()
        lower = sin.tolower()
        OUT.send(lower)


# @component
# @ComponentDescription(
#     "Replace characters apart from EXC in each packet IN with the given OBS and copy to OUT")
# @outport("OUT")
# @inport("IN")
# @inport("OBS")
# @inport("EXC")
# def Obscure(IN, OUT):
#     char
#     obs = ' '  # Default obscure with space
#     pobs = obsport.receive()
#     if (pobs is not None):
#         obs = (pobs.get_content()).char_at(0)
#         self.drop(pobs)
#     obsport.close()
#
#     exc = " "  # Default do not obscure spaces
#     pexc = excport.receive()
#     if (pexc is not None):
#         exc = pexc.get_content()
#         self.drop(pexc)
#     excport.close()
#
#     for pin in IN:
#         out = ""
#         in = pin.get_content()
#         if ( in is not None):
#             in += exc  # add one EXC token as a marker
#             e = in.index_of(exc)
#             s = 0
#             while ( in.length() > out.length() and e > -1):
#                 out += get_string_filled_with((e - s), obs) + exc
#                 # logger.info("in:  |" + in + "|\nout: |" + out + "|")
#                 s = e + exc.length()
#                 e = in.index_of(exc, s)
#             # self.drop the marker
#             out = out.substring(0, out.length() - exc.length())
#             # logger.info("out: |" + out + "|")
#         pin.drop()  # did you hear that?
#
#         pout = self.create(out)
#         outport.send(pout)
#
#
# def get_string_filled_with(number, char filler
#
# ):
# filled = ""
# if (number > 0):
#     char[]
#     fillers = char[number]
#     for (n = 0 n < fillers.length n += 1):
#         fillers[n] = filler
#     filled = String(fillers)
# return filled
#
# """Pad fields to given length in a stream of character-separated records
# """
#
#
# @component
# @ComponentDescription(
#     "Pass through a character SEParated stream, adding PAD up to LIMITS of field lengths")
# @outport("OUT")
# @inport("IN")
# @inport("LIMITS")
# @inport("PAD")
# @inport("SEP")
# def PadFields(Component):
#     # Default separator
#     sep = ","
#
#     # Get separator from SEP IIP
#     psep = sepport.receive()
#     if (psep is not None):
#         sepport.close()
#         sep = psep.get_content()
#         self.drop(psep)
#
#     # Default pad
#     pad = " "
#
#     # get pad from PAD IIP
#     ppad = padport.receive()
#     if (ppad is not None):
#         padport.close()
#         pad = ppad.get_content()
#         self.drop(ppad)
#
#     # get LIMITS
#     int[]
#     nlimits = None
#     plimit = limitport.receive()
#     if (plimit is not None):
#         limitport.close()
#         String[]
#         slimits = (plimit.get_content()).split(sep)
#         nlimits = int[slimits.length]
#         for (j = 0 j < nlimits.length j += 1):
#             nlimits[j] = 0
#             try:
#                 nlimits[j] = Integer.parse_int(slimits[j])
#             except NumberFormatException as e:
#                 e.print_stack_trace()
#         self.drop(plimit)
#
#     # Pass through IN to OUT, PADding fields to LIMITS
#     for pin in IN:
#         in = pin.get_content()
#
#         # Get fields for self record
#         fields = in.split(sep)
#
#         # Pad each field to limit
#         for (i = 0 i < nlimits.length i += 1):
#             while (fields[i].length() < nlimits[i]):
#                 fields[i] += pad
#         spadded = ""
#         for (k = 0 k < fields.length k += 1):
#             spadded += fields[k]
#             if (k < fields.length - 1):
#                 spadded += sep
#
#         # Pass through
#         pout = self.create(spadded)
#         outport.send(pout)
#         pin.drop()


@component
@outport("OUT", type=str)
@inport("IN", description="Strings to have replacement applied", type=str)
@inport("REGEX", description="regular expression",
        type=str)
@inport("REPL", description="Replacement String", type=str)
def ReplaceRegExp(IN, REGEX, REPL, OUT):
    """Replace all occurrences of FIND in each packet IN with the given
    REPL and copy to OUT"""
    find = re.compile(REGEX.receive_once(""))
    repl = REPL.receive_once("")

    for pin in IN:
        text = pin.get_content()
        pin.drop()
        out = find.sub(text, repl)
        OUT.send(out)


"""
 * Replace FIND in each packet IN with the given REPLacement and copy to OUT.
 *
"""


@component
@outport("OUT")
@inport("IN", description="Strings to be modified", type=str)
@inport("FIND", description="Search target", type=str)
@inport("REPL", description="Replacement text", type=str)
def ReplaceString(IN, FIND, REPL, OUT):
    """Replace all occurrences of text matching FIND (case-sensitive) in each
    packet IN with the given REPL and send to OUT"""
    find = FIND.receive_once("")
    repl = REPL.receive("")

    for pin in IN:
        text = pin.get_content()
        out = text.replace(find, repl)
        pin.drop()
        OUT.send(out)


@component
@outport("OUT")
@inport("IN")
def StripPunct(IN, OUT):
    "Remove Unicode punctuation from IN and send stripped packets OUT"
    for pin in IN:
        sin = pin.get_content()
        pin.drop()
        stripped = sin.replace_all("\\p{P}+", "")
        OUT.send(stripped)


@component
@outport("OUT")
@inport("IN")
@inport("MEASURE", type=int)
def WordsToLine(IN, MEASURE, OUT):
    """Take words IN and deliver OUT a line no longer than MEASURE characters"""
    measure = MEASURE.receive_once()
    if measure is None:
        return

    line = ""
    for pin in IN:
        w = pin.get_content().strip()
        pin.drop()

        if len(line) + 1 + len(w) > measure:
            OUT.send(line)
            line = w
        else:
            if line:
                line += " "
            line += w
    if line:
        OUT.send(line)

@component
@outport("OUT")
@inport("IN")
def ConcatStr(IN, OUT):
    """Concatenate all packets in the input stream into one String"""
    result = ""
    for s in IN.iter_content():
        result += s
    OUT.send(result)


@outport("ACC")
@outport("REJ")
@inport("IN")
@inport("TEST")
def StartsWith(IN, TEST, ACC, REJ):
    """Select packets starting with specified string"""
    test_str = TEST.receive_once()

    for p in IN:
        content = p.get_content()
        if content.startswith(test_str):
            ACC.send(p)
        else:
            REJ.send(p)