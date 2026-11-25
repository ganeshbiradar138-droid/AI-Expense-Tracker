setTimeout(()=>document.querySelectorAll(".toast").forEach(x=>{x.style.opacity="0";setTimeout(()=>x.remove(),400)}),3500);
