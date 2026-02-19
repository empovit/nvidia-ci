package testworkloads

import (
	"fmt"
	"time"

	"github.com/golang/glog"
	"github.com/rh-ecosystem-edge/nvidia-ci/internal/gpuparams"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/clients"
	"github.com/rh-ecosystem-edge/nvidia-ci/pkg/pod"
	corev1 "k8s.io/api/core/v1"
)

// Workload manages the lifecycle of a test workload pod.
type Workload struct {
	successCheck func(*pod.Builder) error
	podBuilder   *pod.Builder
}

// newWorkload creates a Workload by creating the pod in the cluster.
func newWorkload(
	apiClient *clients.Settings,
	namespace string,
	podSpec *corev1.Pod,
	successCheck func(*pod.Builder) error,
) (*Workload, error) {
	podSpec.Namespace = namespace

	glog.V(gpuparams.GpuLogLevel).Infof("Creating workload pod %s in namespace %s", podSpec.Name, namespace)

	pb, err := pod.NewBuilderFromDefinition(apiClient, podSpec).Create()
	if err != nil {
		return nil, fmt.Errorf("failed to create pod: %w", err)
	}

	return &Workload{
		successCheck: successCheck,
		podBuilder:   pb,
	}, nil
}

// WaitUntilRunning waits for the pod to reach Running phase.
func (w *Workload) WaitUntilRunning(timeout time.Duration) error {
	return w.WaitUntilStatus(corev1.PodRunning, timeout)
}

// WaitUntilStatus waits for the pod to reach a specific phase.
func (w *Workload) WaitUntilStatus(phase corev1.PodPhase, timeout time.Duration) error {
	if err := w.podBuilder.WaitUntilInStatus(phase, timeout); err != nil {
		return fmt.Errorf("pod failed to reach %s phase: %w", phase, err)
	}

	return nil
}

// WaitUntilSuccess waits for the pod to reach Succeeded phase and validates success criteria.
func (w *Workload) WaitUntilSuccess(timeout time.Duration) error {
	if err := w.WaitUntilStatus(corev1.PodSucceeded, timeout); err != nil {
		return err
	}

	glog.V(gpuparams.GpuLogLevel).Infof("Pod succeeded, validating workload success criteria")
	return w.successCheck(w.podBuilder)
}

// Delete removes the workload pod from the cluster.
func (w *Workload) Delete() error {
	_, err := w.podBuilder.Delete()
	if err != nil {
		return fmt.Errorf("failed to delete pod: %w", err)
	}

	return nil
}
