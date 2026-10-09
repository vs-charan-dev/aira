param([switch]$InputDevices)
# Read-only Windows default endpoint/volume diagnostic. No recording, playback or API calls.
. (Join-Path $PSScriptRoot 'Environment.ps1')
if (-not ('AiraAudioInspection' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
[ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAiraDeviceEnumerator {
    void EnumAudioEndpoints(int flow, int mask, out IntPtr devices);
    void GetDefaultAudioEndpoint(int flow, int role, out IAiraDevice device);
}
[ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAiraDevice {
    void Activate(ref Guid iid, int context, IntPtr parameters, [MarshalAs(UnmanagedType.IUnknown)] out object result);
    void OpenPropertyStore(int access, out IntPtr store);
    void GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
    void GetState(out int state);
}
[ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAiraEndpointVolume {
    void RegisterControlChangeNotify(IntPtr notify);
    void UnregisterControlChangeNotify(IntPtr notify);
    void GetChannelCount(out uint channels);
    void SetMasterVolumeLevel(float level, Guid context);
    void SetMasterVolumeLevelScalar(float level, Guid context);
    void GetMasterVolumeLevel(out float level);
    void GetMasterVolumeLevelScalar(out float level);
    void SetChannelVolumeLevel(uint channel, float level, Guid context);
    void SetChannelVolumeLevelScalar(uint channel, float level, Guid context);
    void GetChannelVolumeLevel(uint channel, out float level);
    void GetChannelVolumeLevelScalar(uint channel, out float level);
    void SetMute([MarshalAs(UnmanagedType.Bool)] bool mute, Guid context);
    void GetMute([MarshalAs(UnmanagedType.Bool)] out bool mute);
}
public class AiraOutputInspection { public string EndpointId; public int VolumePercent; public bool Muted; }
public static class AiraAudioInspection {
    public static AiraOutputInspection Read(int role, int flow) {
        object enumerator = null, endpoint = null, volume = null;
        try {
            enumerator = Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")));
            IAiraDevice device;
            ((IAiraDeviceEnumerator)enumerator).GetDefaultAudioEndpoint(flow, role, out device);
            endpoint = device;
            string id; device.GetId(out id);
            Guid iid = new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
            device.Activate(ref iid, 23, IntPtr.Zero, out volume);
            float scalar; bool muted;
            ((IAiraEndpointVolume)volume).GetMasterVolumeLevelScalar(out scalar);
            ((IAiraEndpointVolume)volume).GetMute(out muted);
            return new AiraOutputInspection { EndpointId = id, VolumePercent = (int)Math.Round(scalar * 100), Muted = muted };
        } finally {
            if (volume != null) Marshal.ReleaseComObject(volume);
            if (endpoint != null) Marshal.ReleaseComObject(endpoint);
            if (enumerator != null) Marshal.ReleaseComObject(enumerator);
        }
    }
}
'@
}
$roles = @('Console', 'Multimedia', 'Communications')
for ($role = 0; $role -lt 3; $role++) {
    try {
        $status = [AiraAudioInspection]::Read($role, [int]$InputDevices.IsPresent)
        $endpointGuid = ($status.EndpointId -split '\.')[-1]
        $direction = if ($InputDevices) { 'Capture' } else { 'Render' }
        $properties = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\$direction\$endpointGuid\Properties"
        try { $speakerName = Get-ItemPropertyValue -LiteralPath $properties -Name '{a45c254e-df1c-4efd-8020-67d146a850e0},2' } catch { $speakerName = 'Default output device' }
        [pscustomobject]@{ Role = $roles[$role]; Device = $speakerName; VolumePercent = $status.VolumePercent; Muted = $status.Muted }
    } catch {
        [pscustomobject]@{ Role = $roles[$role]; Error = $_.Exception.GetBaseException().Message }
    }
}
