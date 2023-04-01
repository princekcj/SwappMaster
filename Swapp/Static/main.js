function openForm() {
  document.getElementById("popuponumberone").style.display = "flex";
}
function closeForm() {
  document.getElementById("popuponumberone").style.display = "none";
}
// When the user clicks anywhere outside of the modal, close it
window.onclick = function (event) {
  let modal = document.getElementById('popuponumberone');
  if (event.target == modal) {
    closeForm();
  }
}


