var counter = 1;
var limit = 10;
function addInput(divName){
     if (counter == limit)  {
          alert("You have reached the limit of adding " + counter + " inputs");
     }
     else {
          var newdiv = document.createElement('div');
          newdiv.innerHTML = "Child " + (counter + 1) + " name:" + "<br><input type='text' name='myInputs[]'>";
          newdiv.innerHTML += " School: " +
          						"<select><option value='HMC'>HMC</option>" + 
          						"<option value='CMC'>CMC</option>" + 
          						"<option value='SCP'>SCP</option>" + 
          						"<option value='POM'>POM</option>" + 
          						"<option value='PIT'>PIT</option></select>";

          document.getElementById(divName).appendChild(newdiv);
          counter++;
     }
}