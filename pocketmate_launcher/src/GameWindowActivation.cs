using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Snowfrost
{
    public static class GameWindowActivation
    {
        delegate bool EnumWindow(IntPtr window, IntPtr parameter);
        [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindow callback,IntPtr parameter);
        [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window,out uint processId);
        [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr window);
        [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr window,uint command);
        [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr window,StringBuilder title,int count);
        [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr window,StringBuilder name,int count);
        [DllImport("user32.dll")] static extern bool IsIconic(IntPtr window);
        [DllImport("user32.dll")] static extern bool ShowWindowAsync(IntPtr window,int command);
        [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
        [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
        [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr window,IntPtr after,int x,int y,int width,int height,uint flags);
        [DllImport("user32.dll")] static extern bool AllowSetForegroundWindow(uint processId);
        [StructLayout(LayoutKind.Sequential)] struct FlashInfo { public uint Size;public IntPtr Window;public uint Flags,Count,Timeout; }
        [DllImport("user32.dll")] static extern bool FlashWindowEx(ref FlashInfo info);

        public static bool IsGameWindow(int expected,int actual,bool visible,bool owned,string title,string windowClass)
        {
            return expected==actual && visible && !owned &&
                (title??"").IndexOf("Minecraft",StringComparison.OrdinalIgnoreCase)>=0 &&
                (windowClass??"").StartsWith("GLFW",StringComparison.OrdinalIgnoreCase);
        }
        static IntPtr FindWindow(int processId)
        {
            IntPtr found=IntPtr.Zero;
            EnumWindows(delegate(IntPtr window,IntPtr unused) {
                uint owner;GetWindowThreadProcessId(window,out owner);
                if(owner!=(uint)processId || !IsWindowVisible(window))return true;
                var title=new StringBuilder(512);var name=new StringBuilder(128);
                GetWindowText(window,title,title.Capacity);GetClassName(window,name,name.Capacity);
                if(!IsGameWindow(processId,(int)owner,true,GetWindow(window,4)!=IntPtr.Zero,title.ToString(),name.ToString()))return true;
                found=window;return false;
            },IntPtr.Zero);
            return found;
        }
        static bool Activate(IntPtr window)
        {
            if(IsIconic(window))ShowWindowAsync(window,9); // Restore only minimized windows.
            // HWND_TOP is a one-time raise, never HWND_TOPMOST.
            SetWindowPos(window,IntPtr.Zero,0,0,0,0,0x0001|0x0002|0x0040);
            return SetForegroundWindow(window) || GetForegroundWindow()==window;
        }
        static void Flash(IntPtr window)
        {
            var info=new FlashInfo {Size=(uint)Marshal.SizeOf(typeof(FlashInfo)),Window=window,Flags=2,Count=3,Timeout=0};
            FlashWindowEx(ref info);
        }
        public static async Task<bool> FocusProcess(Process game,CancellationToken cancel)
        {
            int id=game.Id;
            AllowSetForegroundWindow((uint)id);
            return await FocusWhenReady(
                delegate {try{return !game.HasExited;}catch(InvalidOperationException){return false;}},
                ()=>FindWindow(id),Activate,Flash,ms=>Task.Delay(ms,cancel),480,cancel);
        }
        // Injected callbacks let tests exercise readiness/failure without touching
        // real windows or starting Minecraft, Java or Prism.
        public static async Task<bool> FocusWhenReady(Func<bool> alive,Func<IntPtr> find,
            Func<IntPtr,bool> activate,Action<IntPtr> flash,Func<int,Task> delay,int polls,CancellationToken cancel)
        {
            for(int i=0;i<polls;i++)
            {
                cancel.ThrowIfCancellationRequested();
                if(!alive())return false;
                IntPtr window=find();
                if(window!=IntPtr.Zero)
                {
                    for(int retry=0;retry<3;retry++)
                    {
                        cancel.ThrowIfCancellationRequested();
                        if(!alive())return false;
                        if(find()!=window)break;
                        if(activate(window))return true;
                        await delay(250);
                        // A replaced/closed loading window must never be activated.
                        if(find()!=window)break;
                        if(retry==2){flash(window);return false;}
                    }
                }
                await delay(250);
            }
            return false;
        }
    }
}
