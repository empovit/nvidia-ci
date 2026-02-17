package mig

import (
	"context"
	"fmt"
	"regexp"
	"time"

	"github.com/golang/glog"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/dra"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/helm"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/inittools"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/testworkloads"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/wait"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/namespace"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/nodes"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/nvidiagpu"
	"github.com/rh-ecosystem-edge/nvidia-ci/tests/dra/shared"
	"helm.sh/helm/v3/pkg/action"
	corev1 "k8s.io/api/core/v1"
	resourcev1 "k8s.io/api/resource/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
)

const (
	// MIGDeviceClassName is the DeviceClass for MIG instances
	MIGDeviceClassName = "mig.nvidia.com"
)

var (
	// supportedGPUPattern matches NVIDIA H-series and GB-series GPUs that support MIG
	// Examples: NVIDIA-H100, NVIDIA-H100-PCIE-80GB, NVIDIA-H200-SXM-141GB,
	//           NVIDIA-GB200, NVIDIA-GB200-NVL72, NVIDIA-GB300
	supportedGPUPattern = regexp.MustCompile(`^NVIDIA-(H|GB)\d{3}($|-)`)
)

// hasSupportedGPU checks if the cluster has any nodes with supported GPU models for MIG.
// It validates the nvidia.com/gpu.product node label against the supportedGPUPattern regex.
func hasSupportedGPU() (bool, error) {
	glog.V(gpuparams.GpuLogLevel).Infof("Checking for supported MIG GPU nodes")

	nodeList, err := nodes.List(inittools.APIClient)
	if err != nil {
		return false, fmt.Errorf("failed to list nodes: %w", err)
	}

	for _, node := range nodeList {
		if productLabel, ok := node.Object.Labels[nvidiagpu.GPUProductLabel]; ok {
			glog.V(gpuparams.GpuLogLevel).Infof("Node %s has GPU product: %s", node.Object.Name, productLabel)

			if supportedGPUPattern.MatchString(productLabel) {
				glog.V(gpuparams.GpuLogLevel).Infof("Found supported MIG GPU on node %s: %s", node.Object.Name, productLabel)
				return true, nil
			}
		}
	}

	glog.V(gpuparams.GpuLogLevel).Infof("No supported MIG GPU nodes found in the cluster")
	return false, nil
}

func createMIGResourceClaimTemplate(namespace, name string) error {
	rct := &resourcev1.ResourceClaimTemplate{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
		},
		Spec: resourcev1.ResourceClaimTemplateSpec{
			Spec: resourcev1.ResourceClaimSpec{
				Devices: resourcev1.DeviceClaim{
					Requests: []resourcev1.DeviceRequest{
						{
							Name: "mig",
							Exactly: &resourcev1.ExactDeviceRequest{
								DeviceClassName: MIGDeviceClassName,
							},
						},
					},
				},
			},
		},
	}

	_, err := inittools.APIClient.K8sClient.ResourceV1().
		ResourceClaimTemplates(namespace).
		Create(context.TODO(), rct, metav1.CreateOptions{})
	return err
}

var _ = Describe("DRA MIG", Ordered, Label("dra", "dra-mig"), func() {
	var actionConfig *action.Configuration
	var driver *dra.Driver
	var originalDevicePluginEnabled bool

	BeforeAll(func() {

		By("Verifying minimum Kubernetes version")
		err := shared.VerifyMinimumK8sVersion(inittools.APIClient, "1.35.0")
		Expect(err).ToNot(HaveOccurred(), "Kubernetes version does not meet minimum requirements")

		By("Verifying DRA prerequisites")
		err = shared.VerifyDRAPrerequisites(inittools.APIClient)
		Expect(err).ToNot(HaveOccurred(), "Failed to verify DRA prerequisites")

		By("Checking for supported MIG GPU nodes")
		hasSupported, err := hasSupportedGPU()
		Expect(err).ToNot(HaveOccurred(), "Failed to check for supported GPU nodes")
		Expect(hasSupported).To(BeTrue(), "No supported NVIDIA GPU (H100, H200, GB200, GB300, etc.) found in the cluster. MIG tests require H-series or GB-series GPUs.")

		By("Disabling device plugin for DRA MIG tests")
		devicePluginEnabled, err := shared.SetDevicePluginEnabled(inittools.APIClient, false)
		Expect(err).ToNot(HaveOccurred(), "Failed to disable device plugin")
		originalDevicePluginEnabled = devicePluginEnabled
		glog.V(gpuparams.GpuLogLevel).Infof("Device plugin originally enabled: %v", originalDevicePluginEnabled)

		if originalDevicePluginEnabled {
			DeferCleanup(func() error {
				By("Restoring original device plugin state")
				_, err := shared.SetDevicePluginEnabled(inittools.APIClient, originalDevicePluginEnabled)
				return err
			})
		}

		By("Waiting for GPU capacity on all nodes with GPU present to become 0")
		noGPUCapacityCondition := func(node *corev1.Node) (bool, error) {
			gpuCount, ok := node.Status.Capacity[corev1.ResourceName(nvidiagpu.GPUCapacityKey)]
			if ok {
				glog.V(gpuparams.GpuLogLevel).Infof("Node's %s GPU capacity: %v", node.Name, gpuCount.String())
				return gpuCount.IsZero(), nil
			}
			glog.V(gpuparams.GpuLogLevel).Infof("Node %s does not have GPU capacity", node.Name)
			return true, nil
		}

		err = wait.WaitForNodes(inittools.APIClient, labels.Set{nvidiagpu.GPUPresentLabel: "true"}, noGPUCapacityCondition, 20*time.Second, 10*time.Minute)
		Expect(err).ToNot(HaveOccurred(), "Failed to wait for GPU capacity on GPU nodes to become 0")

		By("Installing DRA Driver's Helm chart")
		actionConfig, err = helm.NewActionConfig(inittools.APIClient, dra.DriverNamespace, gpuparams.GpuLogLevel)
		Expect(err).ToNot(HaveOccurred(), "Failed to create Helm action configuration")

		// For MIG tests, explicitly enable GPU resources
		driver, err = dra.NewDriver()
		Expect(err).ToNot(HaveOccurred(), "Failed to create DRA driver")
		driver.WithGPUResources(true).WithGPUResourcesOverride(true)

		DeferCleanup(func() error {
			By("Uninstalling DRA driver")
			return driver.Uninstall(actionConfig, shared.DriverInstallationTimeout)
		})

		err = driver.Install(actionConfig, shared.DriverInstallationTimeout)
		Expect(err).ToNot(HaveOccurred(), "Failed to install DRA driver")
	})

	Context("When DRA driver is installed with MIG support", func() {
		It("Should allocate a MIG instance using ResourceClaimTemplate", func() {
			names := shared.NewTestNames("mig-test")

			By("Creating test namespace")
			testNs := namespace.NewBuilder(inittools.APIClient, names.Namespace())
			testNs, err := testNs.Create()
			Expect(err).ToNot(HaveOccurred(), "Failed to create test namespace")
			DeferCleanup(func() error {
				By("Cleaning up test namespace")
				return testNs.DeleteAndWait(2 * time.Minute)
			})
			glog.V(gpuparams.GpuLogLevel).Infof("Created test namespace: %s", names.Namespace())

			By("Creating ResourceClaimTemplate for MIG instance")
			err = createMIGResourceClaimTemplate(names.Namespace(), names.ClaimTemplate())
			Expect(err).ToNot(HaveOccurred(), "Failed to create ResourceClaimTemplate")
			glog.V(gpuparams.GpuLogLevel).Infof("Created ResourceClaimTemplate: %s", names.ClaimTemplate())

			By("Creating VectorAdd pod with MIG resource claim")
			rctNamePtr := names.ClaimTemplate()
			resourceClaims := []corev1.PodResourceClaim{
				{
					Name:                      names.Claim(),
					ResourceClaimTemplateName: &rctNamePtr,
				},
			}

			resources := corev1.ResourceRequirements{
				Claims: []corev1.ResourceClaim{
					{
						Name: names.Claim(),
					},
				},
			}

			vectorAdd := testworkloads.NewVectorAdd(names.Pod()).
				WithResources(resources).
				WithResourceClaims(resourceClaims)

			workloadBuilder := testworkloads.NewBuilder(inittools.APIClient, names.Namespace(), vectorAdd).
				Create()
			Expect(workloadBuilder.Error()).ToNot(HaveOccurred(), "Failed to create VectorAdd pod")
			glog.V(gpuparams.GpuLogLevel).Infof("Created VectorAdd pod: %s", names.Pod())

			By("Waiting for VectorAdd pod to succeed")
			workloadBuilder.WaitUntilSuccess(1 * time.Minute)
			Expect(workloadBuilder.Error()).ToNot(HaveOccurred(), "VectorAdd pod did not succeed")
			glog.V(gpuparams.GpuLogLevel).Infof("VectorAdd pod succeeded: %s", names.Pod())
		})
	})
})
