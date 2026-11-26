fn main() -> std::io::Result<()> {
    println!("cargo:rerun-if-changed=tools/release/AirGlove.ico");
    #[cfg(windows)]
    winresource::WindowsResource::new()
        .set_icon("tools/release/AirGlove.ico")
        .set("ProductName", "AirGlove")
        .set("FileDescription", "AirGlove gesture controller")
        .set("OriginalFilename", "AirGlove.exe")
        .compile()?;
    Ok(())
}
