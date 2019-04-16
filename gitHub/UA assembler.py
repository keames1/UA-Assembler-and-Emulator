# This program is an assembler which generates machine code to the universal architecture
# specification. Since the python versions of the emulator and this assembler are mere proofs of
# concept, the output of the assembler, and the input of the emulator are hex code. The final
# version will output binaries, and the final emulator will execute binaries.
import sys
import re

def main ():

    # This program can take the source file and the destination file as command line arguments
    # but for the sake of ease of use, if these command line args are omitted, the assembler will
    # prompt the user for them.
    sourceFilePath = ""
    if len(sys.argv) <= 1:
        # Check whether the user entered the source file as a command line argument and prompt
        # them for it if they haven't.
        sourceFilePath = input("Pleas enter the path of the source file containing main: ")

    else:
        sourceFilePath = sys.argv[1]

    # Read the source code from the file specified and store it in a variable. If the file cannot be
    # accessed, prompt the user to re-enter the file name.
    sourceCode = ""
    while True:
        try:
            with open(sourceFilePath, "r") as f:
                sourceCode = f.read()
                break

        except FileNotFoundError:
            print("The file specified is either inaccessible or non-existent. Please retype the")
            sourceFilePath = input("file path or press ENTER to exit: ")
            if sourceFilePath == "": break

    if sourceFilePath == "": exit()

    # Assemble the source code and store the output in a variable.
    hexcode = assemble(sourceCode)

    # Check whether the user entered the output file as a command line argument and prompt them for one if
    # they haven't.
    outputFilePath = ""
    if len(sys.argv) <= 2:
        print("Please type the name of the file to which you would like to write")
        outputFilePath = input("your assembled program: ")

    else:
        outputFilePath = sys.argv[2]

    # Attempt to write the assembler output to a hex file. Failing that, prompt the user to retype the
    # path to their output.
    while True:
        try:
            with open(outputFilePath, "w") as f:
                f.write(hexcode)
                break

        except FileNotFoundError:
            print("A directory in the specified path to your output file was inaccessible")
            outputFilePath = input("or non-existent. Please retype the file path or press ENTER to exit: ")
            if outputFilePath == "": break
    if outputFilePath == "": exit()
    print("Assembler output written to {}.".format(outputFilePath))

# Named values go in here. Operands can also be aliased, but if it isn't
# data-pool, it goes in oper_ID.pneumonics.
labelsAliasesAndStructMembers = {}
# various patterns for identifying special tokens
validNamePattern = re.compile(r"\A[a-zA-Z_][a-zA-Z_0-9]*\Z")
memoryWindowAddrPattern = re.compile(r"\Aw[0-9A-Fa-f]{2}\Z")
parameterSpaceAddrPattern = re.compile(r"\Ap[0-9A-Fa-f]{2}\Z")
intLiteralPattern = re.compile(r"\A0[bwdq][dx]([0-9A-Fa-f]+)\Z")
charLiteralPattern = re.compile(r"\A\'(.|\n)\Z")
strLiteralPattern = re.compile(r"\A\"(.|\n)*\Z")
regValAddrPattern = re.compile(r"\A(@[a-z]+[0-9]?)\Z")
regOffsetPattern = re.compile(r"\A(@[a-z]+[0-9]?\+)((0x[0-9a-fA-F]+)|([0-9]+))|([a-zA-Z_][a-zA-Z_0-9]*)|([a-zA-Z_][a-zA-Z_0-9]*\.[a-zA-Z_][a-zA-Z_0-9]*)\Z")
flagBitPattern = re.compile(r"\A[A-Z]{2,3}\Z")
SIMDGroupPattern = re.compile(r"\A(w|p)(sg)(0|1)\Z")
structMemberPattern = re.compile(r"\A[a-zA-Z_][a-zA-Z_0-9]*\.[a-zA-Z_][a-zA-Z_0-9]*\Z")
# Assemble the program passed to it in the 'sourceCode' parameter. Output is a hex-string.
def assemble (sourceCode):
    # The parse tree is a list of lists Each line goes into an inner
    # list with the inner list containing one element for each sequence of
    # non-white space characters and character literals prefixed with an '
    # and string literals prefixed with ". Comments are also removed. We
    # don't care here what a programmer has to say about their program.
    parseTree = parse(sourceCode)

    # The hex code for the program goes here, but as the values of address
    # labels haven't been calculated, they're just inserted into the hex code
    # between colons :<address label>:
    partiallyAssembledProgram = ""
    # Structs span multiple lines, so we need a special boolean flag to tell
    # whether we're inside a struct.
    scanningStruct = False
    # The name of a struct followed by a period is prepended onto the name of
    # every struct member. This name mangling means that a programmer
    # can access a struct member with dot notation familiar to anybody
    # who has ever done object-oriented programming. This also gets rid
    # of naming conflicts.
    currentStructName = ""
    # This gets incremented by the size of every instruction or defined memory
    # (dm) segment as the program gets assembled. Basically, the values of
    # address labels are calculated as the assembler works.
    currentAddr = 0
    for i, v in enumerate(parseTree):

        # Check whether or not to start scanning a struct, get the struct name,
        # and ensure the struct header is syntactically correct.
        if v[0] == "struct":
            scanningStruct = True
            if v[1][-1] != "{":
                currentStructName = v[1]
            else:
                currentStructName = v[1][:-1]

            if v[2] != "{" and v[1][-1] != '{':
                print("Syntax error on line {}. Expected '{' at end of struct header.".format(i+1))
                exit()

        # Everything not struct scanning related goes here.
        if not scanningStruct:
            # If the line begins with an instruction pneumonic, assemble the instruction.
            if v[0] in op_codes.pneumonics:
                assembledInstr, size = op_codes.pneumonics[v[0]].assembleFunc(v)
                currentAddr += size
                partiallyAssembledProgram += assembledInstr

            # If the line isn't an instruction, do something else.
            else:
                # Assign address values to labels.
                if v[0][0] == ":":
                    if v[0][-1] != ":":
                        print("Syntax error on line {}. Expected ':' at end of address label.".format(i+1))
                        exit()
                    if validNamePattern.search(v[1][1:-1]):
                        # The convoluted slicing expression seen here takes the '0x' off the output of the
                        # hex function and creates a fixed-length hex value. In this case, a 16-bit address
                        # (2 hex digits per byte.)
                        labelsAliasesAndStructMembers[v[1][1:-1]] = "a" + ("0000" + hex(currentAddr)[2:])[-4:]
                    else:
                        print("Syntax error on line {}. A name must begin with a letter or an".format(i + 1))
                        print("underscore followed by zero or more letters, numbers, or underscores")
                        exit()
                elif v[0] == "alias":
                    # The syntax is "alias <The alias of the operand>:\s<The operand to be aliased>"
                    # The use of this feature is strictly limited to data-pool addresses,
                    # register value addresses, registers and literals. First we check whether the alias
                    # is a valid name and inform the programmer if the name they chose is invalid.
                    if v[1][-1] != ":":
                        print("Syntax error on line {}. Expected ':' after alias name.".format(i+1))

                    if validNamePattern.search(v[1][:-1]):
                        # Here's what happens when the programmer wants to alias a memory window or parameter
                        # space operand:
                        if memoryWindowAddrPattern.search(v[2]) or parameterSpaceAddrPattern.search(v[2]):
                            dataPoolAddr = int(v[2][1:], 16)
                            if dataPoolAddr > 0x7F:
                                print("Syntax error on line {}. Parameter space and memory window addresses".format(
                                    i + 1))
                                print("may not be larger than 127 (0x7F).")
                                exit()
                            if v[0] == "p":

                                dataPoolAddr += 0x80
                            elif v[0] == "w":
                                # Here, we don't need to do anything further to dataPoolAddr,
                                # we just need to yell at the programmer and exit the program
                                # if they give us a number greater that 127.
                                pass

                            labelsAliasesAndStructMembers[v[1][:-1]] = "d" + ("0000" + hex(dataPoolAddr)[2:])[-2:]

                        elif v[2] in oper_ID.pneumonics:
                            # No need to check whether the programmer tried to alias a register offset. The offset
                            # would be in the same token, thereby preventing a match. Example: @wi3+42
                            oper_ID.pneumonics[v[1]] = oper_ID.pneumonics[v[2]]

                        elif charLiteralPattern.search(v[2]):
                            labelsAliasesAndStructMembers[v[1][-1]] = "l" + ("0000" + hex(ord(v[2][1]))[2:])[-2:]

                        elif intLiteralPattern.search(v[2]):
                            labelsAliasesAndStructMembers[v[1][-1]] = "l" + convertIntLiteral(v[2])

                    else:
                        print("Syntax error on line {}. A name must begin with a letter or an".format(i+1))
                        print("underscore followed by zero or more letters, numbers, or underscores")
                        exit()

                elif v[0] == "dm":

                    for dmToken in v[1:]:

                        # Insert all the values listed in the defined memory section into the program and add their
                        # sizes in bytes to currentAddr for continued address calculation
                        if strLiteralPattern.search(dmToken):
                            if len(dmToken) > 1:
                                for singleChar in dmToken[1:]:
                                    partiallyAssembledProgram += ("0000" + hex(ord(singleChar))[2:])[-2:]
                                    currentAddr += 1

                        elif charLiteralPattern.search(dmToken):
                            partiallyAssembledProgram += ("0000" + hex(ord(dmToken[1]))[2:])[-2:]
                            currentAddr += 1

                        elif intLiteralPattern.search(dmToken):
                            newNumStr = convertIntLiteral(dmToken)
                            currentAddr = newNumStr // 2
                            partiallyAssembledProgram += newNumStr

                        elif dmToken in labelsAliasesAndStructMembers:
                            currentAddr += len(labelsAliasesAndStructMembers[dmToken]) // 2
                            partiallyAssembledProgram += "l" + labelsAliasesAndStructMembers[dmToken][1:]

                        else:
                            if dmToken not in oper_ID.pneumonics:
                                # This is necessary because if the size of something isn't known and it's going into
                                # memory, it thwarts any attempt to calculate addresses automatically.
                                print("Naming error on line {}. Names used in defined memory sections must be defined".format(i+1))
                                print("prior to reference. '{}' was not recognized.".format(dmToken))
                                exit()
                            else:
                                print("Aliasing error on line {}. Neither operands, nor their aliases may be included".format(i+1))
                                print("in a defined memory section.")
                                exit()

        else:
            # Struct scanning goes here. Struct members are assigned literal values with the syntax:
            # structMemberName:  decimalValue
            # Struct members are meant to be used as offsets, so they are always 16-bit.
            if v[0] != "struct" and v[2] != "{":
                if validNamePattern.search(v[0][:-1]):
                    if v[0][-1] != ":":
                        print("Syntax error on line {}. Expected ':' at the end of struct member name.".format(i+1))
                    try:
                        if v[1][-1] == "}":
                            labelsAliasesAndStructMembers[currentStructName + "." + v[0][:-1]] = "l" + ("0000" + hex(int(v[1]))[2:])[-4:]
                        else:
                            labelsAliasesAndStructMembers[currentStructName + "." + v[0][:-1]] = "l" + ("0000" + hex(int(v[1][:-1]))[2:])[-4:]
                    except ValueError:
                        print("Syntax Error on line {}. The value assingned to {}".format(i+1, currentStructName + "." + v[0][:-1]))
                        print("Cannot be converted to an integer.")
                        exit()
                else:
                    print("Syntax error on line {}. Names must begin in a letter or an".format(i+1))
                    print("underscore followed by 0 or more letters, numbers and underscores.")


        if v[-1][-1] == "}": scanningStruct = False

    assembledProgram = ""
    scanningNamedValue = False
    for v in partiallyAssembledProgram:

        pass

    return assembledProgram

# Convert UA assembly integer literals into a plain hexadecimal notation of the length specified in the word length field of the literal.
def convertIntLiteral (intLiteral):
    if intLiteral[0] != "0":
        raise ValueError("UA assembly integer literals must begin with 0 followed by b, w, d, or q to indicate word size followed by x or d for hexadecimal or decimal respectively.")

    returnValue = ""
    if intLiteral[1] == "b":
        if intLiteral[2] == "x":
            returnValue = ("00" + intLiteral[3:])[-2:]
        elif intLiteral[2] == "d":
            returnValue = ("00" + hex(int(intLiteral[3:]))[2:])[-2:]
        else:
            raise ValueError("UA assembly integer literals must begin with 0 followed by b, w, d, or q to indicate word size followed by x or d for hexadecimal or decimal respectively.")

    elif intLiteral[1] == "w":
        if intLiteral[2] == "x":
            returnValue = ("0000" + intLiteral[3:])[-4:]
        elif intLiteral[2] == "d":
            returnValue = ("0000" + hex(int(intLiteral[3:]))[2:])[-4:]
        else:
            raise ValueError("UA assembly integer literals must begin with 0 followed by b, w, d, or q to indicate word size followed by x or d for hexadecimal or decimal respectively.")

    elif intLiteral[1] == "d":
        if intLiteral[2] == "x":
            returnValue = ("00000000" + intLiteral[3:])[-8:]
        elif intLiteral[2] == "d":
            returnValue = ("00000000" + hex(int(intLiteral[3:]))[2:])[-8:]
        else:
            raise ValueError("UA assembly integer literals must begin with 0 followed by b, w, d, or q to indicate word size followed by x or d for hexadecimal or decimal respectively.")

    elif intLiteral[1] == "q":
        if intLiteral[2] == "x":
            returnValue = ("0000000000000000" + intLiteral[3:])[-16:]
        elif intLiteral[2] == "d":
            returnValue = ("0000000000000000" + hex(int(intLiteral[3:]))[2:])[-16:]
        else:
            raise ValueError("UA assembly integer literals must begin with 0 followed by b, w, d, or q to indicate word size followed by x or d for hexadecimal or decimal respectively.")

    else :
        raise ValueError("UA assembly integer literals must begin with 0 followed by b, w, d, or q to indicate word size followed by x or d for hexadecimal or decimal respectively.")

    return returnValue

# Parse the code into a list of lists with the outer list containing
# one list for each line of code and the elements of the inner lists
# containing all non-whitespace character sequences, string and char
# literals in the order they appear in the source code.
def parse (sourceCode):
    parsedCode = [[""]]         # The parse tree goes here
    scanningStrLiteral = False  # String and character literals may contain spaces, so they
    scanningChrLiteral = False  # require special treatment.
    ignoringComment = False     #
    for charIndex, charValue in enumerate(sourceCode):

        if charValue == "/" and sourceCode[charIndex + 1] == "/":
            ignoringComment = True

        if charValue == "\n":
            ignoringComment = False

        if not ignoringComment:
            if charValue == "\"" and not scanningChrLiteral and sourceCode[charIndex - 1] != "\\":
                scanningStrLiteral = not scanningStrLiteral
                if not scanningStrLiteral: # This runs when the end of a string literal is reached.
                    parsedCode[-1][-1] += "\""
                    parsedCode[-1][-1] = eval(parsedCode[-1][-1])
                    parsedCode[-1][-1] = "\"" + parsedCode[-1][-1]
                    parsedCode[-1].append("")

            if charValue == "'" and not scanningStrLiteral and sourceCode[charIndex - 1] != "\\":
                scanningChrLiteral = not scanningChrLiteral
                if not scanningChrLiteral: # This runs when the end of a char literal is reached.
                    parsedCode[-1][-1] += "'"
                    parsedCode[-1][-1] = eval(parsedCode[-1][-1])
                    if len(parsedCode[-1][-1]) > 1:
                        print("Syntax error on line {}. The expression in a character literal".format(len(parsedCode)))
                        print("must resolve to a single character!")
                        exit()
                    parsedCode[-1][-1] = "'" + parsedCode[-1][-1]
                    parsedCode[-1].append("")

            if charValue != "\n":
                if scanningChrLiteral or scanningStrLiteral:
                    # Character literals may only be one character long. Otherwise, they are treated
                    # the same way as strings.
                    parsedCode[-1][-1] += charValue
                else:
                    # Every sequence of non-whitespace characters outside string and character
                    # literals is a single token.
                    if charValue != " " and charValue != "\t":
                        parsedCode[-1][-1] += charValue
                    else:
                        parsedCode[-1].append("")
            else:
                # When linebreaks are found, create a new list to represent the next line.
                if scanningStrLiteral:
                    print("Syntax error on line {}. Expected end of string literal but found".format(len(parsedCode)))
                    print("end of line.")
                    exit()
                if scanningChrLiteral:
                    print("Syntax error on line {}. Expected end of character literal but found".format(len(parsedCode)))
                    print("end of line.")
                    exit()
                parsedCode.append([""])

    # Remove the blank lines and empty strings that occur when the algorithm above is applied.
    parseTreeWithEmptyStrings = parsedCode
    parsedCode = []
    for line in parseTreeWithEmptyStrings:
        if line != [""] and line != []:
            parsedCode.append([])
            for token in line:
                if token != "":
                    parsedCode[-1].append(token)

    parseTreeWithBlankLines = parsedCode
    parsedCode = []
    for line in parseTreeWithBlankLines:
        if line != []:
            parsedCode.append(line)

    return parsedCode

class Instruction:
    def __init__(self, opCode, basicSize, assembleFunc):
        self.opCode = opCode
        self.basicSize = basicSize
        self.assembleFunc = assembleFunc

    # A wrapper for the assemble function which passes the instructions basic information along
    # with a line of code from the parse tree and the optional address parameter.
    def assembleInstruction (self, line):
        return self.assembleFunc(line, self.opCode, self.basicSize)

def unParse (line):
    result = ""
    for i in line:
        result += " " + i

    return result.strip()

def parseOperand (token):
    isNonDataPool = False
    payload = ""; hasPayload = False
    payloadSize = 0
    # Parse the first operand, determine whether it's data-pool or non-data-pool, set its
    # operand type bit accordingly, and get the appropriate operand ID and payload.
    operandField = ""
    if memoryWindowAddrPattern.search(token):
        operandField = ("00" + hex(int(token[1:], 16))[2:])[-2:]

    elif parameterSpaceAddrPattern.search(token):
        operandField = int(token[1:], 16) + 128
        operandField = ("00" + hex(operandField)[2:])[-2:]

    elif intLiteralPattern.search(token):
        operObject = oper_ID.pneumonics[token[0:2]]
        payloadSize = operObject.payloadSize
        payload = convertIntLiteral(token)
        hasPayload = True
        isNonDataPool = True
        operandField = ("00" + hex(operObject.operandID)[2:])[-2:]

    elif charLiteralPattern.search(token):
        operObject = oper_ID.pneumonics["0b"]
        payload = ("00" + hex(ord(token[1])[2:]))[-2:]
        payloadSize = 1
        hasPayload = True
        isNonDataPool = True
        operandField = ("00" + hex(operObject.operandID)[2:])[-2:]

    elif token in labelsAliasesAndStructMembers:
        valType = labelsAliasesAndStructMembers[token][0]
        isNonDataPool = True
        if valType == "a":
            hasPayload = True
            isNonDataPool = True
            payload = labelsAliasesAndStructMembers[token][1:]
            payloadSize = oper_ID.pneumonics["@"].payloadSize
            operandField = ("00" + hex(oper_ID.pneumonics["@"].operandID)[2:])[-2:]

        elif valType == "l":
            hasPayload = True
            isNonDataPool = True
            payload = labelsAliasesAndStructMembers[token][1:]
            if len(payload) == 2:
                operandField = ("00" + hex(oper_ID.pneumonics["0b"].operandID)[2:])[-2:]
                payloadSize = oper_ID.pneumonics["0b"].payloadSize
            elif len(payload) == 4:
                operandField = ("00" + hex(oper_ID.pneumonics["0w"].operandID)[2:])[-2:]
                payloadSize = oper_ID.pneumonics["0w"].payloadSize
            elif len(payload) == 8:
                operandField = ("00" + hex(oper_ID.pneumonics["0d"].operandID)[2:])[-2:]
                payloadSize = oper_ID.pneumonics["0d"].payloadSize
            elif len(payload) == 16:
                operandField = ("00" + hex(oper_ID.pneumonics["0q"].operandID)[2:])[-2:]
                payloadSize = oper_ID.pneumonics["0q"].payloadSize

        elif valType == "d":
            operandField = labelsAliasesAndStructMembers[token][1:]

    elif regOffsetPattern.search(token):
        isNonDataPool = True
        hasPayload = True
        opPneumonicEndPos = token.find("+") + 1
        opPneumonic = token[0: opPneumonicEndPos]
        operandField = ("00" + hex(oper_ID.pneumonics[opPneumonic].operandID)[2:])[-2:]
        payloadSize = oper_ID.pneumonics[opPneumonic].payloadSize
        offset = token[opPneumonicEndPos:]
        if offset[0] == "x":
            try:
                payload = ("0000" + hex(int(offset[1:], 16))[2:])[-4:]
            except ValueError:
                print("Syntax error: Named values to be used as register offsets cannot begin")
                print("with a lowercase 'x' as in the name '{}'.".format(offset))
                exit()

        elif offset[0] in "0123456789":
            try:
                payload = ("0000" + hex(int(offset, 16))[2:])[-4:]
            except ValueError:
                print("Syntax error: Invalid integer literal or invalid name {}.".format(offset))
                exit()
        else:
            payload = ":" + offset + ":"

    elif regValAddrPattern.search(token):
        isNonDataPool = True
        operandField = ("00" + hex(oper_ID.pneumonics[token].operandID)[2:])[-2:]

    elif token in oper_ID.pneumonics:
        isNonDataPool = True
        operandField = ("00" + hex(oper_ID.pneumonics[token].operandID)[2:])[-2:]

    else:
        isNonDataPool = True
        hasPayload = True
        payload = ":" + token + ":"
        payloadSize = 2
        operandField = ("00" + hex(oper_ID.pneumonics["@"].operandID)[2:])[-2:]

    return isNonDataPool, hasPayload, operandField, payload, payloadSize

# These functions are attached to instances of Instruction. They accept the current line in
# their first argument, the op-code of the instruction they're assembling in the second, and
# their size sans payload in the third. They return a tuple with the instruction assembled into
# hex-code with named values marked by colons and the beginning and end at index 0 and the size
# of the instruction in bytes at index 1. There are many instructions in the instruction set
# which can be assembled in the same manner, though they perform different operations so, only
# these 9 functions are necessary.
def iOneByteFunc (line, opCode, basicSize):
    pass

def iTwoStandardOperandsFunc (line, opCode, basicSize):
    pass

def iIgnFunc (line, opCode, basicSize):
    pass

def iModeFunc (line, opCode, basicSize):
    pass

def iOneStandardOperandFunc (line, opCode, basicSize):
    pass

def iCmpFunc (line, opCode, basicSize):
    pass

def iBranchFunc (line, opCode, basicSize):
    pass

def iOneWordFunc (line, opCode, basicSize):
    pass

def iNOPFunc (line, opCode, basicSize):
    pass

# This class is a name-space for global constants. All the basic information about each
# instruction in the instruction set is listed here.
class op_codes:
    iExit = 0x00

    iAdd = 0x01; iSub = 0x02; iMul = 0x03; iDiv = 0x04; iIgn = 0x05; iMode = 0x06
    iAnd = 0x07; iOr = 0x08; iNor = 0x09; iXor = 0x0A; iNot = 0x0B; iCmp = 0x0C

    iJfl = 0x0D; iSfl = 0x0E; iCall = 0x0F; iRet = 0x10

    iMov = 0x11; iMw = 0x12; iAlloc = 0x13

    iIOchan = 0x14; iIn = 0x15; iOut = 0x16; iOuts = 0x17; iSeek = 0x18; iInth = 0x19

    iNOP = 0x1A

    pneumonics = {"exit":Instruction(iExit, 2, iOneByteFunc),
                  "add":Instruction(iAdd, 3, iTwoStandardOperandsFunc),
                  "sub":Instruction(iSub, 3, iTwoStandardOperandsFunc),
                  "mul":Instruction(iMul, 4, iTwoStandardOperandsFunc),
                  "div":Instruction(iDiv, 4, iTwoStandardOperandsFunc),
                  "ign":Instruction(iIgn, 1, iIgnFunc),
                  "mode":Instruction(iMode, 2, iModeFunc),
                  "and":Instruction(iAnd, 3, iTwoStandardOperandsFunc),
                  "or":Instruction(iOr, 3, iTwoStandardOperandsFunc),
                  "nor":Instruction(iNor, 3, iTwoStandardOperandsFunc),
                  "xor":Instruction(iXor, 3, iTwoStandardOperandsFunc),
                  "not":Instruction(iNot, 2, iOneStandardOperandFunc),
                  "cmp":Instruction(iCmp, 3, iTwoStandardOperandsFunc),
                  "jfl":Instruction(iJfl, 3, iBranchFunc),
                  "sfl":Instruction(iSfl, 3, iBranchFunc),
                  "call":Instruction(iCall, 3, iOneWordFunc),
                  "ret":Instruction(iRet, 2, iOneByteFunc),
                  "mov":Instruction(iMov, 3, iTwoStandardOperandsFunc),
                  "mw":Instruction(iMw, 2, iOneStandardOperandFunc),
                  "alloc":Instruction(iAlloc, 2, iOneStandardOperandFunc),
                  "IOchan":Instruction(iIOchan, 3, iOneStandardOperandFunc),
                  "in":Instruction(iIn, 3, iTwoStandardOperandsFunc),
                  "out":Instruction(iOut, 3, iTwoStandardOperandsFunc),
                  "outs":Instruction(iOuts, 2, iOneStandardOperandFunc),
                  "seek":Instruction(iSeek, 2, iOneStandardOperandFunc),
                  "inth":Instruction(iInth, 3, iOneWordFunc),
                  "NOP":Instruction(iNOP, 1, iNOPFunc)}

class Operand:

    def __init__(self, operandID, payloadSize = 0):
        self.operandID = operandID
        self.payloadSize = payloadSize

# This class is also a name space for global constants. Operand IDs and basic information about
# operands are stored here.
class oper_ID:
    wi0 = 0x00; wi1 = 0x01; wi2 = 0x02; wi3 = 0x03
    pi0 = 0x04; pi1 = 0x05; pi2 = 0x06; pi3 = 0x07

    wi0Offset = 0x08; wi1Offset = 0x09; wi2Offset = 0x0A; wi3Offset = 0x0B
    pi0Offset = 0x0C; pi1Offset = 0x0D; pi2Offset = 0x0E; pi3Offset = 0x0F

    atWi0 = 0x10; atWi1 = 0x11; atWi2 = 0x12; atWi3 = 0x13
    atPi0 = 0x14; atPi1 = 0x15; atPi2 = 0x16; atPi3 = 0x17

    ar0 = 0x18; ar1 = 0x19; ar2 = 0x1A; ar3 = 0x1B
    ar0Offset = 0x1C; ar1Offset = 0x1D; ar2Offset = 0x1E; ar3Offset = 0x1F
    atAr0 = 0x20; atAr1 = 0x21; atAr2 = 0x22; atAr3 = 0x23

    ip = 0x25
    sp = 0x25; spOffset = 0x26; atSp = 0x27
    ap = 0x28; apOffset = 0x29; atAp = 0x2A
    wl = 0x2B; wlOffset = 0x2C; atWl = 0x2D
    flg = 0x2E
    rs = 0x2F

    lit8 = 0x30; lit16 = 0x31; litAddr = 0x32; lit32 = 0x33; lit64 = 0x34

    ZF = 0x35; SF = 0x36; OF = 0x37; NOF = 0x38; TF = 0x39; EF = 0x3A; DZF = 0x3B; RF = 0x3E
    SEF = 0x3D; FMF = 0x3E; WLB = 0x3F

    wsg0 = 0x40; wsg1 = 0x41
    psg0 = 0x42; psg1 = 0x43

    pneumonics = {
        "0b": Operand(lit8, 1),
        "0w": Operand(lit16, 2),
        "@": Operand(litAddr, 2),
        "0d": Operand(lit32, 4),
        "0q": Operand(lit64, 8),
        "wi0": Operand(wi0, 0),
        "wi1": Operand(wi1, 0),
        "wi2": Operand(wi2, 0),
        "wi3": Operand(wi3, 0),
        "pi0": Operand(pi0, 0),
        "pi1": Operand(pi1, 0),
        "pi2": Operand(pi2, 0),
        "pi3": Operand(pi3, 0),
        "ar0": Operand(ar0, 0),
        "ar1": Operand(ar1, 0),
        "ar2": Operand(ar2, 0),
        "ar3": Operand(ar3, 0),
        "sp": Operand(sp, 0),
        "ap": Operand(ap, 0),
        "wl": Operand(wl, 0),
        "flg": Operand(flg, 0),
        "rs": Operand(rs, 0),
        "@wi0": Operand(atWi0, 0),
        "@wi1": Operand(atWi1, 0),
        "@wi2": Operand(atWi2, 0),
        "@wi3": Operand(atWi3, 0),
        "@pi0": Operand(atPi0, 0),
        "@pi1": Operand(atPi1, 0),
        "@pi2": Operand(atPi2, 0),
        "@pi3": Operand(atPi3, 0),
        "@ar0": Operand(atAr0, 0),
        "@ar1": Operand(atAr1, 0),
        "@ar2": Operand(atAr2, 0),
        "@ar3": Operand(atAr3, 0),
        "@sp": Operand(atSp, 0),
        "@ap": Operand(atAp, 0),
        "@wl": Operand(atWl, 0),
        "@wi0+": Operand(wi0Offset, 2),
        "@wi1+": Operand(wi1Offset, 2),
        "@wi2+": Operand(wi2Offset, 2),
        "@wi3+": Operand(wi3Offset, 2),
        "@pi0+": Operand(pi0Offset, 2),
        "@pi1+": Operand(pi1Offset, 2),
        "@pi2+": Operand(pi2Offset, 2),
        "@pi3+": Operand(pi3Offset, 2),
        "@ar0+": Operand(ar0Offset, 2),
        "@ar1+": Operand(ar1Offset, 2),
        "@ar2+": Operand(ar2Offset, 2),
        "@ar3+": Operand(ar3Offset, 2),
        "@sp+": Operand(spOffset, 2),
        "@ap+": Operand(apOffset, 2),
        "@wl+": Operand(wlOffset, 2),
        "ZF": Operand(ZF, 0),
        "SF": Operand(SF, 0),
        "OF": Operand(OF, 0),
        "NOF": Operand(NOF, 0),
        "TF": Operand(TF, 0),
        "EF": Operand(EF, 0),
        "DZF": Operand(DZF, 0),
        "RF": Operand(RF, 0),
        "SEF": Operand(SEF, 0),
        "FMF": Operand(FMF, 0),
        "WLB": Operand(WLB, 0),
        "wsg0": Operand(wsg0, 0),
        "wsg1": Operand(wsg1, 0),
        "psg0": Operand(psg0, 0),
        "psg1": Operand(psg1, 0)
    }

if __name__ == "__main__":
    main()
