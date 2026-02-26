package wait

import (
	"context"
	"fmt"
	"time"

	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/nodes"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/nvidiagpu"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/olm"
	corev1 "k8s.io/api/core/v1"
	k8serrors "k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/util/wait"
)

// ClusterPolicyReady Waits until clusterPolicy is Ready.
func ClusterPolicyReady(apiClient *clients.Settings, clusterPolicyName string, pollInterval, timeout time.Duration) error {
	return wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			clusterPolicy, err := nvidiagpu.Pull(apiClient, clusterPolicyName)

			if err != nil {
				glog.V(gpuparams.GpuLogLevel).Infof("ClusterPolicy pull from cluster error: %s\n", err)

				return false, err
			}

			if clusterPolicy.Object != nil && clusterPolicy.Object.Status.State == "ready" {
				glog.V(gpuparams.GpuLogLevel).Infof("ClusterPolicy %s in now in %s state",
					clusterPolicy.Object.Name, clusterPolicy.Object.Status.State)

				// this exits out of the PollUntilContextTimeout()
				return true, nil
			}
			if clusterPolicy.Object == nil {
				glog.V(gpuparams.GpuLogLevel).Info("ClusterPolicy object is nil")
				return false, nil
			}

			glog.V(gpuparams.GpuLogLevel).Infof("ClusterPolicy %s in now in %s state",
				clusterPolicy.Object.Name, clusterPolicy.Object.Status.State)

			return false, nil
		})
}

// ClusterPolicyNotReady Waits until clusterPolicy is NotReady.
func ClusterPolicyNotReady(apiClient *clients.Settings, clusterPolicyName string, pollInterval,
	timeout time.Duration) error {
	glog.V(gpuparams.Gpu10LogLevel).Infof("wait.ClusterPolicyNotReady: %s", clusterPolicyName)
	return wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			clusterPolicy, err := nvidiagpu.Pull(apiClient, clusterPolicyName)

			if err != nil {
				glog.V(gpuparams.GpuLogLevel).Infof("ClusterPolicy pull from cluster error: %s\n", err)

				return false, err
			}

			if clusterPolicy.Object != nil && clusterPolicy.Object.Status.State == "notReady" {
				glog.V(gpuparams.GpuLogLevel).Infof("ClusterPolicy %s is now in %s state",
					clusterPolicy.Object.Name, clusterPolicy.Object.Status.State)

				// this exits out of the PollUntilContextTimeout()
				return true, nil
			}
			if clusterPolicy.Object == nil {
				glog.V(gpuparams.GpuLogLevel).Info("ClusterPolicy object is nil")
				return false, nil
			}

			glog.V(gpuparams.GpuLogLevel).Infof("ClusterPolicy %s is currently in %s state",
				clusterPolicy.Object.Name, clusterPolicy.Object.Status.State)

			return false, nil
		})
}

// CSVSucceeded waits for a defined period of time for CSV to be in Succeeded state.
func CSVSucceeded(apiClient *clients.Settings, csvName, csvNamespace string, pollInterval,
	timeout time.Duration) error {
	return wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			csvPulled, err := olm.PullClusterServiceVersion(apiClient, csvName, csvNamespace)

			if err != nil {
				glog.V(gpuparams.GpuLogLevel).Infof("ClusterServiceVersion pull from cluster error: %s\n", err)

				return false, err
			}

			if csvPulled.Object.Status.Phase == "Succeeded" {
				glog.V(gpuparams.GpuLogLevel).Infof("ClusterServiceVersion %s in now in %s state",
					csvPulled.Object.Name, csvPulled.Object.Status.Phase)

				// this exists out of the wait.PollImmediate().
				return true, nil
			}

			glog.V(gpuparams.GpuLogLevel).Infof("clusterPolicy %s in now in %s state",
				csvPulled.Object.Name, csvPulled.Object.Status.Phase)

			return false, err
		})
}

// CSVDeployedInNamespace polls until a CSV different from previousCSVName appears in the namespace,
// returning the new CSV name. Use after a subscription channel upgrade to wait for the new CSV.
func CSVDeployedInNamespace(apiClient *clients.Settings, previousCSVName, namespace string,
	pollInterval, timeout time.Duration) (string, error) {
	var newCSVName string
	err := wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			csvList, err := olm.ListClusterServiceVersion(apiClient, namespace)
			if err != nil {
				return false, err
			}
			for _, csv := range csvList {
				if csv.Definition.Name != previousCSVName {
					newCSVName = csv.Definition.Name
					return true, nil
				}
			}
			return false, nil
		})
	return newCSVName, err
}

// DeploymentCreated waits for a defined period of time for deployment to be created.
func DeploymentCreated(apiClient *clients.Settings, deploymentName, deploymentNamespace string, pollInterval,
	timeout time.Duration) bool {
	err := wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			_, err := apiClient.AppsV1Interface.Deployments(deploymentNamespace).Get(
				ctx, deploymentName, metav1.GetOptions{})
			if k8serrors.IsNotFound(err) {
				return false, nil
			}
			if err != nil {
				return false, err
			}

			glog.V(gpuparams.GpuLogLevel).Infof("Deployment '%s' in namespace '%s' has been created",
				deploymentName, deploymentNamespace)

			return true, nil
		})

	return err == nil
}

// NodeLabelExists waits for at least one node with the specified label selector to have a label with the given key and value.
func NodeLabelExists(apiClient *clients.Settings, labelKey, labelValue string, nodeSelector labels.Set, pollInterval,
	timeout time.Duration) error {
	glog.V(gpuparams.Gpu10LogLevel).Infof("Waiting for node label '%s'='%s' on nodes with selector: %v", labelKey, labelValue, nodeSelector)
	return wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			nodeBuilders, err := nodes.List(apiClient, metav1.ListOptions{LabelSelector: nodeSelector.String()})

			if err != nil {
				glog.V(gpuparams.GpuLogLevel).Infof("Error listing nodes: %v", err)

				return false, err
			}

			for _, node := range nodeBuilders {
				glog.V(gpuparams.Gpu10LogLevel).Infof("Checking node '%s' for label '%s'", node.Object.Name, labelKey)
				if value, ok := node.Object.Labels[labelKey]; ok && value == labelValue {
					glog.V(gpuparams.Gpu100LogLevel).Infof("Found label '%s' with value '%s' on node '%s'", labelKey, labelValue, node.Object.Name)

					// this exits out of the PollUntilContextTimeout()
					return true, nil
				} else {
					glog.V(gpuparams.Gpu10LogLevel).Infof("Label '%s'='%s' not found on node '%s'", labelKey, labelValue, node.Object.Name)
					return false, nil
				}
			}

			glog.V(gpuparams.Gpu10LogLevel).Infof("Label '%s'='%s' not found yet, retrying...", labelKey, labelValue)

			return false, nil
		})
}

// WaitForNodes waits for nodes matching the selector to satisfy the condition function.
func WaitForNodes(apiClient *clients.Settings, nodeSelector labels.Set, condition func(*corev1.Node) (bool, error), pollInterval, timeout time.Duration) error {
	glog.V(gpuparams.Gpu10LogLevel).Infof("Waiting for nodes with selector: %v", nodeSelector)

	return wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			nodeBuilders, err := nodes.List(apiClient, metav1.ListOptions{
				LabelSelector: nodeSelector.String(),
			})

			if err != nil {
				return false, fmt.Errorf("error listing nodes: %w", err)
			}

			if len(nodeBuilders) == 0 {
				return false, fmt.Errorf("no nodes found matching selector %v", nodeSelector)
			}

			for _, nodeBuilder := range nodeBuilders {
				satisfied, err := condition(nodeBuilder.Object)
				if err != nil {
					return false, fmt.Errorf("failed to check node %s: %w", nodeBuilder.Object.Name, err)
				}

				if !satisfied {
					return false, nil
				}
				glog.V(gpuparams.GpuLogLevel).Infof("Node %s satisfies the required condition", nodeBuilder.Object.Name)
			}

			glog.V(gpuparams.GpuLogLevel).Info("All nodes satisfy the required condition")
			return true, nil
		})
}

// WaitForObjectToExist polls until checkFn returns true, indicating the object exists.
// Use this before calling status-check methods that do not tolerate object absence.
func WaitForObjectToExist(checkFn func() bool, pollInterval, timeout time.Duration) error {
	return wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true,
		func(ctx context.Context) (bool, error) { return checkFn(), nil })
}

// DaemonSetReady waits for a specific DaemonSet to have all pods ready.
func DaemonSetReady(apiClient *clients.Settings, daemonSetName, namespace string, pollInterval, timeout time.Duration) error {
	glog.V(gpuparams.Gpu10LogLevel).Infof("Waiting for DaemonSet '%s' in namespace '%s' to be ready", daemonSetName, namespace)
	return wait.PollUntilContextTimeout(
		context.TODO(), pollInterval, timeout, true, func(ctx context.Context) (bool, error) {
			ds, err := apiClient.DaemonSets(namespace).Get(ctx, daemonSetName, metav1.GetOptions{})

			if err != nil {
				return false, fmt.Errorf("error getting DaemonSet '%s' in namespace '%s': %w", daemonSetName, namespace, err)
			}

			// Verify the generation observed by the DaemonSet controller matches the spec generation
			if ds.Status.ObservedGeneration != ds.Generation {
				glog.V(gpuparams.GpuLogLevel).Infof("DaemonSet '%s' in namespace '%s': ObservedGeneration %d != Generation %d",
					daemonSetName, namespace, ds.Status.ObservedGeneration, ds.Generation)
				return false, nil
			}

			// Make sure all the updated pods have been scheduled
			if ds.Status.UpdatedNumberScheduled != ds.Status.DesiredNumberScheduled {
				glog.V(gpuparams.GpuLogLevel).Infof("DaemonSet '%s' in namespace '%s': %d/%d pods updated",
					daemonSetName, namespace, ds.Status.UpdatedNumberScheduled, ds.Status.DesiredNumberScheduled)
				return false, nil
			}

			// Verify all nodes have available pods (ready for at least minReadySeconds)
			// NumberAvailable only counts nodes with the current revision's pods that are available,
			// unlike NumberReady which can include old revision pods during rolling updates
			available := ds.Status.NumberAvailable
			desired := ds.Status.DesiredNumberScheduled

			glog.V(gpuparams.GpuLogLevel).Infof("DaemonSet '%s' in namespace '%s': %d/%d pods available",
				daemonSetName, namespace, available, desired)

			if desired > 0 && available == desired {
				glog.V(gpuparams.GpuLogLevel).Infof("DaemonSet '%s' in namespace '%s' is now ready",
					daemonSetName, namespace)
				return true, nil
			}

			return false, nil
		})
}
