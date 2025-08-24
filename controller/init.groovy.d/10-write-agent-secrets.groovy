import jenkins.model.Jenkins

def outDir = new File("/keys"); outDir.mkdirs()
def j = Jenkins.get()

def want = ["ubuntu_jnlp","ubuntu_ws"]

want.each { nodeName ->
  int tries = 120  // ~120s total at 1s per try
  while (tries-- > 0) {
    def comp = j.getComputer(nodeName)
    def secret = comp?.getJnlpMac()
    if (secret) {
      new File(outDir, "${nodeName}.secret").text = secret + "\n"
      println "Wrote secret for ${nodeName}"
      return // next node
    }
    Thread.sleep(1000)
  }
  println "ERROR: Timed out waiting for node '${nodeName}' or its secret"
}
