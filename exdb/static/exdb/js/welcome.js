// yes this code is bad
// yes we are leaving it for now
// we want to get as much coverage as possible in our tests for obvious reasons
// once the project is complex enough that deleting the below
// does not reduce coverage this file can be deleted

console.log('hello');

global = true;

function f() {
    for (var i = 0; i < 100; i++) {
        if (i > 100) {
            console.log('this shouldn\'t execute');
        }
        if (global) {
            console.log(global);
        }
    }
}
function main(){
    f();
}
