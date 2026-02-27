import lldb

def StringSummaryProvider(valobj, internal_dict):
    # Try to access _M_dataplus._M_p
    # If fails, try to look at memory manually
    
    # This is a heuristic for GCC's std::string
    # It has _M_dataplus, _M_string_length, etc.
    
    try:
        # If we have debug info, this works
        dataplus = valobj.GetChildMemberWithName('_M_dataplus')
        if dataplus.IsValid():
            mp = dataplus.GetChildMemberWithName('_M_p')
            if mp.IsValid():
                data = mp.GetSummary()
                if data: return data
                # If summary is missing, read memory
                addr = mp.GetValueAsUnsigned(0)
                if addr == 0: return '""'
                
                # Read string from memory
                error = lldb.SBError()
                s = valobj.GetProcess().ReadCStringFromMemory(addr, 1024, error)
                if error.Success():
                    return f'"{s}"'
    except:
        pass
        
    # Fallback for missing debug info (incomplete type)
    # Assuming standard layout: pointer at offset 0
    try:
        addr = valobj.GetAddress().GetLoadAddress(valobj.GetTarget())
        if addr == lldb.LLDB_INVALID_ADDRESS:
            addr = valobj.GetValueAsUnsigned(0)
            
        # We need to read the pointer at this address.
        # But wait, std::string is a struct. 
        # _M_dataplus is the first member.
        # _M_dataplus has _M_p as first member (usually).
        
        # So dereferencing the address of the string object gives the address of the char buffer.
        error = lldb.SBError()
        pointer_val = valobj.GetProcess().ReadPointerFromMemory(addr, error)
        if error.Success() and pointer_val != 0:
            s = valobj.GetProcess().ReadCStringFromMemory(pointer_val, 1024, error)
            if error.Success():
                return f'"{s}"'
    except:
        pass
        
    return ""

def WxStringSummaryProvider(valobj, internal_dict):
    # wxString is usually a wrapper around std::basic_string or compatible
    # In wx 3.x with std::string enabled, it might inherit from it or have it as member
    
    # Try 1: check if it has m_impl
    try:
        impl = valobj.GetChildMemberWithName('m_impl')
        if impl.IsValid():
            return StringSummaryProvider(impl, internal_dict)
    except:
        pass
        
    # Try 2: treat as std::string directly (inheritance)
    res = StringSummaryProvider(valobj, internal_dict)
    if res and res != "":
        return res
        
    return ""

def WxEventSummaryProvider(valobj, internal_dict):
    # For incomplete wxEvent, we try to resolve the vtable to get dynamic type
    
    try:
        addr = valobj.GetAddress().GetLoadAddress(valobj.GetTarget())
        if addr == lldb.LLDB_INVALID_ADDRESS:
             # Maybe it's a pointer or reference, get its value
             addr = valobj.GetValueAsUnsigned(0)
             
        if addr == 0:
            return "NULL"

        # Read vtable pointer (first word)
        error = lldb.SBError()
        vptr = valobj.GetProcess().ReadPointerFromMemory(addr, error)
        
        if error.Success() and vptr != 0:
            # Resolve symbol for vptr
            addr_obj = valobj.GetTarget().ResolveLoadAddress(vptr)
            sym = addr_obj.GetSymbol()
            if sym.IsValid():
                name = sym.GetName()
                # Name is like "vtable for wxCommandEvent"
                # Demangle usually happens automatically in LLDB API or we can just parse
                if "vtable for " in name:
                    return name.replace("vtable for ", "") + f" @ {hex(addr)}"
                return name + f" @ {hex(addr)}"
    except:
        pass
        
    return f"wxEvent @ {hex(valobj.GetValueAsUnsigned(0))}"

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('type summary add -F lldb_formatters.StringSummaryProvider "std::string"')
    debugger.HandleCommand('type summary add -F lldb_formatters.StringSummaryProvider "std::__cxx11::string"')
    debugger.HandleCommand('type summary add -F lldb_formatters.StringSummaryProvider "std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >"')
    
    debugger.HandleCommand('type summary add -F lldb_formatters.WxStringSummaryProvider "wxString"')
    debugger.HandleCommand('type summary add -F lldb_formatters.WxEventSummaryProvider "wxEvent" -C yes')
    debugger.HandleCommand('type summary add -F lldb_formatters.WxEventSummaryProvider "wxCommandEvent" -C yes')
    debugger.HandleCommand('type summary add -F lldb_formatters.WxEventSummaryProvider "wxNotifyEvent" -C yes')
    debugger.HandleCommand('type summary add -F lldb_formatters.WxEventSummaryProvider "wxMouseEvent" -C yes')
    debugger.HandleCommand('type summary add -F lldb_formatters.WxEventSummaryProvider "wxKeyEvent" -C yes')
