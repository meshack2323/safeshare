async function getKey() {
  const res = await fetch('/api/key');
  const { key } = await res.json();
  return key;
}

async function upload() {
  const text = document.getElementById("text").value;
  const file = document.getElementById("file").files[0];
  const passcode = document.getElementById("passcode").value;

  const formData = new FormData();
  formData.append("passcode", passcode);

  if (text) {
    const key = await getKey();
    const encrypted = btoa(unescape(encodeURIComponent(text))); // simplified
    formData.append("type", "text");
    formData.append("encrypted", encrypted);
  } else if (file) {
    formData.append("type", "file");
    formData.append("file", file);
  } else {
    alert("Please enter a message or upload a file.");
    return;
  }

  const res = await fetch('/api/upload', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.link) {
    document.getElementById("link").innerText = window.location.origin + data.link;
  } else {
    alert("Error uploading.");
  }
}

async function viewMessage(msg_id) {
  const passcode = document.getElementById("passcode").value;

  const formData = new FormData();
  formData.append("passcode", passcode);

  const res = await fetch('/api/view/' + msg_id, {
    method: "POST",
    body: formData,
  });

  const data = await res.json();
  const output = document.getElementById("output");

  if (data.error) {
    output.innerText = data.error;
    return;
  }

  if (data.type === "text") {
    const decrypted = decodeURIComponent(escape(atob(data.data))); // simplified
    output.innerText = decrypted;
  } else if (data.type === "file") {
    output.innerText = `File received: ${data.filename}`;
  }
}
