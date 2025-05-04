function main() {
    let prev_src = "";
    function download_image(src, file_name) {
        if (src === prev_src) {
            return;
        }
        prev_src = src;
        fetch(src).then(
            (image)=> {
                image.blob().then(
                    (imageBlob)=>{
                        const imageURL = URL.createObjectURL(imageBlob)
                        var link = document.createElement('a');
                        link.href = imageURL;
                        link.download = file_name;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    }
                )
                
            }
        )
    }
    function num_to_file_name(num_text) {
        const num = Number(num_text);
        if (!num) {
            console.log(`Cannot convert ${num_text} to number`);
            throw new Error();
        }
        return "Yonkoma JP " + String(num).padStart(4, '0') + ".png";
    }
    function download() {
        const num = document.getElementsByClassName("popup_comicNum")[0].innerText;
        const file_name = num_to_file_name(num);
        download_image(
            document.getElementsByClassName("mainImg")[0].src, 
            file_name);
        const button = document.getElementsByClassName("popup_navBox-next")[0];
        if (button) {
            button.click();
        }
        setTimeout(download, 5000);
    }
    download();
}
main()
