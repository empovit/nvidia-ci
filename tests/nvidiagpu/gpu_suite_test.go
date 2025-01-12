package nvidiagpu

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"testing"

	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/reporter"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients"

	"github.com/rh-ecosystem-edge/nvidia-ci/internal/inittools"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/tsparams"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _, currentFile, _, _ = runtime.Caller(0)

func TestGPUDeploy(t *testing.T) {
	_, reporterConfig := GinkgoConfiguration()
	reporterConfig.JUnitReport = inittools.GeneralConfig.GetJunitReportPath(currentFile)

	RegisterFailHandler(Fail)
	RunSpecs(t, "GPU", Label(tsparams.Labels...), reporterConfig)
}

var _ = JustAfterEach(func() {
	reporter.ReportIfFailed(
		CurrentSpecReport(), currentFile, tsparams.ReporterNamespacesToDump, tsparams.ReporterCRDsToDump, clients.SetScheme)

	dumpDir := inittools.GeneralConfig.GetDumpFailedTestReportLocation(currentFile)
	if dumpDir != "" {
		artifactDir := fmt.Sprintf("ARTIFACT_DIR=%s", dumpDir)
		cmd := exec.Command("./gpu-operator-must-gather.sh")
		cmd.Env = append(os.Environ(), artifactDir)
		_, err := cmd.CombinedOutput()
		if err != nil {
			glog.Errorf("Error running gpu-operator-must-gather.sh script %v", err)
		}
	}
})
