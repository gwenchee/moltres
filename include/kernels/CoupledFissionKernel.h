#ifndef COUPLEDFISSIONKERNEL_H
#define COUPLEDFISSIONKERNEL_H

#include "Kernel.h"

//Forward Declarations
class CoupledFissionKernel;

template<>
InputParameters validParams<CoupledFissionKernel>();

class CoupledFissionKernel : public Kernel
{
public:
  CoupledFissionKernel(const InputParameters & parameters);

protected:
  virtual Real computeQpResidual();
  virtual Real computeQpJacobian();
  virtual Real computeQpOffDiagJacobian(unsigned int jvar);

  const MaterialProperty<std::vector<Real> > & _nsf;
  const MaterialProperty<std::vector<Real> > & _d_nsf_d_temp;
  const MaterialProperty<std::vector<Real> > & _chi;
  const MaterialProperty<std::vector<Real> > & _d_chi_d_temp;
  int _group;
  int _num_groups;
  unsigned int _temp_id;
  std::vector<const VariableValue *> _group_fluxes;
  std::vector<unsigned int> _flux_ids;
};

#endif //COUPLEDFISSIONKERNEL_H
