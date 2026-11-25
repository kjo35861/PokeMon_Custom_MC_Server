using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

static class PlayerSetup
{
    static readonly byte[] Marker = Encoding.ASCII.GetBytes("PMSETUP1");
    const string Launcher = "PocketmateLauncher.exe";
    [STAThread]
    static void Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--verify")
        {
            string sandbox = Path.Combine(Path.GetTempPath(),"Pocketmate-Setup-Verify-"+Guid.NewGuid().ToString("N"));
            try
            {
                string installation = Path.Combine(sandbox,"Custom Folder");
                Install(installation,false);
                string shortcut = CreateShortcut(installation,sandbox);
                dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
                dynamic link = shell.CreateShortcut(shortcut);
                if (!File.Exists(Path.Combine(installation,"client-pack.json")) ||
                    !File.Exists(Path.Combine(installation,"launcher-config.json")) ||
                    !File.Exists((string)link.TargetPath) || (string)link.WorkingDirectory != installation)
                    throw new IOException("Setup verification failed.");
            }
            finally
            {
                if (Directory.Exists(sandbox)) Directory.Delete(sandbox,true);
            }
            return;
        }
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        var form = new Form { Text = "포켓메이트 설치 마법사", Width = 570, Height = 250,
            StartPosition = FormStartPosition.CenterScreen, FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false };
        var label = new Label { Text = "포켓메이트를 설치할 폴더를 선택하세요.", Left = 20, Top = 25, Width = 510 };
        var path = new TextBox { Left = 20, Top = 61, Width = 400,
            Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","Pocketmate") };
        var browse = new Button { Text = "찾아보기…", Left = 430, Top = 58, Width = 100 };
        var desktop = new CheckBox { Text = "바탕화면에 바로가기 만들기", Left = 20, Top = 98, Width = 350, Checked = true };
        var status = new Label { Left = 20, Top = 134, Width = 505, Height = 24 };
        var action = new Button { Text = "설치", Left = 430, Top = 164, Width = 100 };
        form.Controls.AddRange(new Control[] { label, path, browse, desktop, status, action });
        form.AcceptButton = action;
        bool busy = false, done = false;
        form.FormClosing += (s,e) => { if (busy) e.Cancel = true; };
        browse.Click += (s,e) => {
            using (var dialog = new FolderBrowserDialog())
                if (dialog.ShowDialog(form) == DialogResult.OK)
                    path.Text = Path.Combine(dialog.SelectedPath,"Pocketmate");
        };
        action.Click += async (s,e) => {
            if (done) { form.Close(); return; }
            busy = true; action.Enabled = browse.Enabled = path.Enabled = desktop.Enabled = false;
            status.Text = "런처와 클라이언트 팩을 설치하고 있습니다…";
            try {
                string target = Path.GetFullPath(path.Text.Trim());
                bool shortcut = desktop.Checked;
                await Task.Run(() => Install(target,shortcut));
                done = true; action.Text = "완료";
                status.Text = "설치 완료. 바로가기 또는 설치 폴더에서 실행하세요.";
            } catch (Exception error) {
                MessageBox.Show(form,error.Message,"설치 실패",MessageBoxButtons.OK,MessageBoxIcon.Error);
                status.Text = "";
            } finally {
                busy = false; action.Enabled = true;
                if (!done) browse.Enabled = path.Enabled = desktop.Enabled = true;
            }
        };
        Application.Run(form);
    }
    static void Install(string path,bool shortcut)
    {
        if (File.Exists(path) || (Directory.Exists(path) && Directory.GetFileSystemEntries(path).Length != 0))
            throw new IOException("새 폴더 또는 비어 있는 폴더를 선택하세요.");
        Directory.CreateDirectory(path);
        string prefix = path.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        WithArchive(zip => {
            foreach (var item in zip.Entries)
            {
                string destination = Path.GetFullPath(Path.Combine(path,item.FullName));
                if (!destination.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))
                    throw new IOException("설치 파일의 경로를 확인해주세요.");
                if (item.Name.Length == 0) { Directory.CreateDirectory(destination); continue; }
                Directory.CreateDirectory(Path.GetDirectoryName(destination));
                using (var source = item.Open())
                using (var destinationStream = new FileStream(destination,FileMode.CreateNew))
                    source.CopyTo(destinationStream);
            }
        });
        if (shortcut) CreateShortcut(path,Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory));
    }
    static string CreateShortcut(string path,string desktop)
    {
        string link = Path.Combine(desktop,"포켓메이트 런처.lnk");
        dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
        dynamic shortcut = shell.CreateShortcut(link);
        shortcut.TargetPath = Path.Combine(path,Launcher);
        shortcut.WorkingDirectory = path;
        shortcut.IconLocation = Path.Combine(path,Launcher) + ",0";
        shortcut.Save();
        return link;
    }
    static void WithArchive(Action<ZipArchive> action)
    {
        string temporary = Path.GetTempFileName();
        try {
            using (var input = File.OpenRead(Assembly.GetExecutingAssembly().Location))
            using (var reader = new BinaryReader(input,Encoding.ASCII))
            {
                input.Seek(-16,SeekOrigin.End);
                long length = reader.ReadInt64();
                if (Encoding.ASCII.GetString(reader.ReadBytes(8)) != Encoding.ASCII.GetString(Marker)
                    || length <= 0 || length > input.Length - 16)
                    throw new IOException("설치 패키지가 손상됐습니다.");
                input.Seek(-16-length,SeekOrigin.End);
                using (var output = File.Create(temporary))
                {
                    byte[] buffer = new byte[1024*1024];
                    while (length > 0)
                    {
                        int n = input.Read(buffer,0,(int)Math.Min(length,buffer.Length));
                        if (n == 0) throw new EndOfStreamException();
                        output.Write(buffer,0,n); length -= n;
                    }
                }
            }
            using (var zip = ZipFile.OpenRead(temporary)) action(zip);
        } finally { File.Delete(temporary); }
    }
}
