import binascii
import ctypes
import struct
import sys
import re
from itertools import islice    
import time

def main():
    if len(sys.argv) !=2:
        sys.exit('Missing a parameter. (You need a file name.)') #Error Check
    
    #Error check to make sure the user has RDBEx
    try:
        RtlDecompressBufferEx = ctypes.windll.ntdll.RtlDecompressBufferEx
    except AttributeError:
        sys.exit('You must use at least Windows 8.')

    sizeList=[]
    offsetList=[]
    zeroList=[]
    zeroLimit = 200
    fileNum=1
    i = 0
    algorithm = 4
    ntstatus = 1

    NULL = ctypes.POINTER(ctypes.c_uint)()
    SIZE_T = ctypes.c_uint
    DWORD = ctypes.c_uint32
    USHORT = ctypes.c_uint16
    UCHAR  = ctypes.c_ubyte
    ULONG = ctypes.c_uint32

    RtlGetCompressionWorkSpaceSize = ctypes.windll.ntdll.RtlGetCompressionWorkSpaceSize

    bufferWorkspaceSize = ULONG()
    fragmentWorkspaceSize = ULONG()
    finalFileSize = ULONG()

    RtlGetCompressionWorkSpaceSize(USHORT(algorithm),
     ctypes.byref(bufferWorkspaceSize),
     ctypes.byref(fragmentWorkspaceSize))
    workspace = (UCHAR * bufferWorkspaceSize.value)()

    with open(sys.argv[1], 'rb') as fileIn: #sys.argv[1] is the provided file from the command line
        buffer = fileIn.read()
        hexPat= re.compile(b'MAM')
        pos = 0
        for match in re.finditer(hexPat, buffer):
            print("FOUND MAM here: {}".format(match.start()))
            len_uncompressed = struct.unpack("<I", buffer[match.start() + 4 : match.start() + 8])[0]
            if len_uncompressed >= 512 and len_uncompressed < 10*1024*1024:
                print("Seems like a valid pf")
                offsetList.append(match.start())
                sizeList.append(len_uncompressed)
            else:
                print("Not valid pf, len was {}".format(len_uncompressed))
            pos += match.start() + 3
            match = re.search(hexPat, buffer[pos:])

        zeroPat = re.compile(b"\\x00\\x00")

        for fileStart in offsetList:
            listPointer= 0 #Increments upon successful file carve, gets next size
            uncompressedSize = sizeList[listPointer]
            listPointer += 1
            fileIn.seek(fileStart)
            uncompressBuffer = (UCHAR * uncompressedSize)()
            newBuffer=fileIn.read(300000)
            for zeroGrab in islice(re.finditer(zeroPat, newBuffer), zeroLimit):
                zeroList.append(zeroGrab.end()) #Clear this out with new fileStart
            #print(len(zeroList))
            #for x in zeroList:
            #   print(x)

            for zeroCounter in zeroList:
                if ntstatus == 0:
                    break
                fileIn.seek(fileStart + 8)
                print(zeroCounter)
                compressedSize = zeroCounter
                compressedFile = fileIn.read(compressedSize)
                compressedBuffer = (UCHAR * compressedSize).from_buffer_copy(compressedFile)
                #print(uncompressBuffer)
                #print(uncompressedSize)
                #print(compressedBuffer)
                #print(compressedSize)
                
                ntstatus = RtlDecompressBufferEx(
                USHORT(algorithm),
                ctypes.byref(uncompressBuffer),
                ULONG(uncompressedSize),
                ctypes.byref(compressedBuffer),
                ULONG(compressedSize),
                ctypes.byref(finalFileSize),
                ctypes.byref(workspace))

                #time.sleep(1)

                print(ntstatus)

        with open("carvedfile%s.pf" % fileNum, 'wb') as fileOut:
            fileNum += 1
            fileOut.write(bytearray(uncompressBuffer))
            fileOut.flush()

main()