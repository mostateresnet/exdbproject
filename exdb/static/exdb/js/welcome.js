console.log('hello');

global = true

function f() {
    for (var i = 0; i < 100; i++) {
        if (i > 100) {
            console.log('this shouldn\'t execute')
        }
        if (global) {
            console.log(global)
        }
    }
}
function main(){
    f();
}
